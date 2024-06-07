from __future__ import annotations

import logging
import time
from abc import abstractmethod
from copy import copy
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any, ContextManager, NamedTuple

from kevm_pyk.kevm import KEVM, KEVMSemantics, _process_jumpdests
from kevm_pyk.utils import KDefinition__expand_macros, abstract_cell_vars, run_prover
from pathos.pools import ProcessPool  # type: ignore
from pyk.cterm import CTerm, CTermSymbolic
from pyk.kast.inner import KApply, KSequence, KSort, KToken, KVariable, Subst
from pyk.kast.manip import flatten_label, set_cell
from pyk.kcfg import KCFG, KCFGExplore
from pyk.kore.rpc import KoreClient, TransportType, kore_server
from pyk.prelude.bytes import bytesToken
from pyk.prelude.collections import list_empty, map_empty, map_of, set_empty, set_of
from pyk.prelude.k import GENERATED_TOP_CELL
from pyk.prelude.kbool import FALSE, TRUE, notBool
from pyk.prelude.kint import intToken
from pyk.prelude.ml import mlEqualsFalse, mlEqualsTrue
from pyk.prelude.string import stringToken
from pyk.proof import ProofStatus
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.utils import run_process, unique

from .foundry import Foundry, foundry_to_xml
from .hevm import Hevm
from .options import ConfigType, TraceOptions
from .solc_to_k import Contract, hex_string_to_int
from .utils import parse_test_version_tuple

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Final

    from pyk.kast.inner import KInner
    from pyk.kore.rpc import KoreServer

    from .deployment import DeploymentStateEntry
    from .options import ProveOptions

_LOGGER: Final = logging.getLogger(__name__)


def foundry_prove(
    options: ProveOptions,
    foundry: Foundry,
    deployment_state_entries: Iterable[DeploymentStateEntry] | None = None,
) -> list[APRProof]:
    if options.workers <= 0:
        raise ValueError(f'Must have at least one worker, found: --workers {options.workers}')
    if options.max_iterations is not None and options.max_iterations < 0:
        raise ValueError(
            f'Must have a non-negative number of iterations, found: --max-iterations {options.max_iterations}'
        )

    if options.use_booster:
        try:
            run_process(('which', 'kore-rpc-booster'), pipe_stderr=True).stdout.strip()
        except CalledProcessError:
            raise RuntimeError(
                "Couldn't locate the kore-rpc-booster RPC binary. Please put 'kore-rpc-booster' on PATH manually or using kup install/kup shell."
            ) from None

    foundry.mk_proofs_dir()

    if options.include_summaries and options.cse:
        raise AttributeError('Error! Cannot use both --cse and --include-summary.')

    summary_ids: list[str] = (
        [
            foundry.get_apr_proof(include_summary.id).id
            for include_summary in collect_tests(foundry, options.include_summaries, reinit=False)
        ]
        if options.include_summaries
        else []
    )

    if options.cse:
        exact_match = options.config_type == ConfigType.SUMMARY_CONFIG
        test_suite = collect_tests(
            foundry, options.tests, reinit=options.reinit, return_empty=True, exact_match=exact_match
        )
        for test in test_suite:
            if not isinstance(test.method, Contract.Method) or test.method.function_calls is None:
                continue

            test_version_tuples = [
                parse_test_version_tuple(t) for t in test.method.function_calls if t not in summary_ids
            ]

            if len(test_version_tuples) > 0:
                _LOGGER.info(f'For test {test.name}, found external calls: {test_version_tuples}')
                new_prove_options = copy(options)
                new_prove_options.tests = test_version_tuples
                new_prove_options.config_type = ConfigType.SUMMARY_CONFIG
                summary_ids.extend(p.id for p in foundry_prove(new_prove_options, foundry, deployment_state_entries))

    exact_match = options.config_type == ConfigType.SUMMARY_CONFIG
    test_suite = collect_tests(foundry, options.tests, reinit=options.reinit, exact_match=exact_match)
    test_names = [test.name for test in test_suite]
    print(f'Running functions: {test_names}')

    contracts = [(test.contract, test.version) for test in test_suite]
    setup_method_tests = collect_setup_methods(
        foundry, contracts, reinit=options.reinit, setup_version=options.setup_version
    )
    setup_method_names = [test.name for test in setup_method_tests]

    _LOGGER.info(f'Running tests: {test_names}')

    _LOGGER.info(f'Updating digests: {test_names}')
    for test in test_suite:
        test.method.update_digest(foundry.digest_file)

    _LOGGER.info(f'Updating digests: {setup_method_names}')
    for test in setup_method_tests:
        test.method.update_digest(foundry.digest_file)

    def _run_prover(_test_suite: list[FoundryTest], include_summaries: bool = False) -> list[APRProof]:
        return _run_cfg_group(
            tests=_test_suite,
            foundry=foundry,
            options=options,
            summary_ids=(summary_ids if include_summaries else []),
            deployment_state_entries=deployment_state_entries,
        )

    if options.run_constructor:
        constructor_tests = collect_constructors(foundry, contracts, reinit=options.reinit)
        constructor_names = [test.name for test in constructor_tests]

        _LOGGER.info(f'Updating digests: {constructor_names}')
        for test in constructor_tests:
            test.method.update_digest(foundry.digest_file)

        _LOGGER.info(f'Running initialization code for contracts in parallel: {constructor_names}')
        results = _run_prover(constructor_tests, include_summaries=False)
        failed = [proof for proof in results if not proof.passed]
        if failed:
            raise ValueError(f'Running initialization code failed for {len(failed)} contracts: {failed}')

    _LOGGER.info(f'Running setup functions in parallel: {setup_method_names}')
    results = _run_prover(setup_method_tests, include_summaries=False)

    failed = [proof for proof in results if not proof.passed]
    if failed:
        raise ValueError(f'Running setUp method failed for {len(failed)} contracts: {failed}')

    _LOGGER.info(f'Running test functions in parallel: {test_names}')
    results = _run_prover(test_suite, include_summaries=True)

    if options.xml_test_report:
        foundry_to_xml(foundry, results)

    return results


class FoundryTest(NamedTuple):
    contract: Contract
    method: Contract.Method | Contract.Constructor
    version: int

    @property
    def name(self) -> str:
        return f'{self.contract.name_with_path}.{self.method.signature}'

    @property
    def id(self) -> str:
        return f'{self.name}:{self.version}'

    @property
    def unparsed(self) -> tuple[str, int]:
        return self.name, self.version


def collect_tests(
    foundry: Foundry,
    tests: Iterable[tuple[str, int | None]] = (),
    *,
    reinit: bool,
    return_empty: bool = False,
    exact_match: bool = False,
) -> list[FoundryTest]:
    if not tests and not return_empty:
        tests = [(test, None) for test in foundry.all_tests]
    matching_tests = []
    for test, version in tests:
        matching_tests += [(sig, version) for sig in foundry.matching_sigs(test, exact_match=exact_match)]
    tests = list(unique(matching_tests))

    res: list[FoundryTest] = []
    for sig, ver in tests:
        contract, method = foundry.get_contract_and_method(sig)
        version = foundry.resolve_proof_version(sig, reinit, ver)
        res.append(FoundryTest(contract, method, version))
    return res


def collect_setup_methods(
    foundry: Foundry, contracts: Iterable[tuple[Contract, int]] = (), *, reinit: bool, setup_version: int | None = None
) -> list[FoundryTest]:
    res: list[FoundryTest] = []
    contract_names: set[str] = set()  # ensures uniqueness of each result (Contract itself is not hashable)
    for contract, test_version in contracts:
        if contract.name_with_path in contract_names:
            continue
        contract_names.add(contract.name_with_path)

        method = contract.method_by_name.get('setUp')
        if not method:
            continue
        version = foundry.resolve_setup_proof_version(
            f'{contract.name_with_path}.setUp()', reinit, test_version, setup_version
        )
        res.append(FoundryTest(contract, method, version))
    return res


def collect_constructors(
    foundry: Foundry, contracts: Iterable[tuple[Contract, int]] = (), *, reinit: bool
) -> list[FoundryTest]:
    res: list[FoundryTest] = []
    contract_names: set[str] = set()  # ensures uniqueness of each result (Contract itself is not hashable)
    for contract, _ in contracts:
        if contract.name_with_path in contract_names:
            continue
        contract_names.add(contract.name_with_path)

        method = contract.constructor
        if not method:
            continue
        version = foundry.resolve_proof_version(f'{contract.name_with_path}.init', reinit, None)
        res.append(FoundryTest(contract, method, version))
    return res


class OptionalKoreServer(ContextManager['OptionalKoreServer']):
    @abstractmethod
    def port(self) -> int: ...


class FreshKoreServer(OptionalKoreServer):
    _server: KoreServer

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._server = kore_server(*args, **kwargs)

    def __enter__(self) -> FreshKoreServer:
        return self

    def __exit__(self, *args: Any) -> None:
        self._server.__exit__(*args)

    def port(self) -> int:
        return self._server.port


class PreexistingKoreServer(OptionalKoreServer):
    _port: int

    def __init__(self, port: int) -> None:
        self._port = port

    def __enter__(self) -> PreexistingKoreServer:
        return self

    def __exit__(self, *args: Any) -> None: ...

    def port(self) -> int:
        return self._port


def _run_cfg_group(
    tests: list[FoundryTest],
    foundry: Foundry,
    options: ProveOptions,
    summary_ids: Iterable[str],
    deployment_state_entries: Iterable[DeploymentStateEntry] | None = None,
) -> list[APRProof]:
    def init_and_run_proof(test: FoundryTest) -> APRFailureInfo | Exception | None:
        proof = None
        if Proof.proof_data_exists(test.id, foundry.proofs_dir):
            proof = foundry.get_apr_proof(test.id)
            if proof.passed:
                return None
        start_time = time.time() if proof is None or proof.status == ProofStatus.PENDING else None

        kore_rpc_command = None
        if isinstance(options.kore_rpc_command, str):
            kore_rpc_command = options.kore_rpc_command.split()

        def select_server() -> OptionalKoreServer:
            if options.port is not None:
                return PreexistingKoreServer(options.port)
            else:
                return FreshKoreServer(
                    definition_dir=foundry.kevm.definition_dir,
                    llvm_definition_dir=foundry.llvm_library if options.use_booster else None,
                    module_name=foundry.kevm.main_module,
                    command=kore_rpc_command,
                    bug_report=options.bug_report,
                    smt_timeout=options.smt_timeout,
                    smt_retry_limit=options.smt_retry_limit,
                    smt_tactic=options.smt_tactic,
                    haskell_threads=options.max_frontier_parallel,
                )

        with select_server() as server:

            def create_kcfg_explore() -> KCFGExplore:
                if options.maude_port is None:
                    dispatch = None
                else:
                    dispatch = {
                        'execute': [('localhost', options.maude_port, TransportType.HTTP)],
                        'simplify': [('localhost', options.maude_port, TransportType.HTTP)],
                        'add-module': [
                            ('localhost', options.maude_port, TransportType.HTTP),
                            ('localhost', server.port(), TransportType.SINGLE_SOCKET),
                        ],
                    }
                client = KoreClient(
                    'localhost',
                    server.port(),
                    bug_report=options.bug_report,
                    bug_report_id=test.id,
                    dispatch=dispatch,
                )
                cterm_symbolic = CTermSymbolic(
                    client,
                    foundry.kevm.definition,
                    trace_rewrites=options.trace_rewrites,
                )
                return KCFGExplore(
                    cterm_symbolic,
                    kcfg_semantics=KEVMSemantics(auto_abstract_gas=options.auto_abstract_gas),
                    id=test.id,
                )

            if proof is None:
                # With CSE, top-level proof should be a summary if it's not a test or setUp function
                if options.cse and options.config_type == ConfigType.TEST_CONFIG and not test.contract.is_test_contract:
                    options.config_type = ConfigType.SUMMARY_CONFIG

                proof = method_to_apr_proof(
                    test=test,
                    foundry=foundry,
                    kcfg_explore=create_kcfg_explore(),
                    bmc_depth=options.bmc_depth,
                    run_constructor=options.run_constructor,
                    use_gas=options.use_gas,
                    deployment_state_entries=deployment_state_entries,
                    summary_ids=summary_ids,
                    active_symbolik=options.with_non_general_state,
                    hevm=options.hevm,
                    config_type=options.config_type,
                    trace_options=TraceOptions(
                        {
                            'active_tracing': options.active_tracing,
                            'trace_memory': options.trace_memory,
                            'trace_storage': options.trace_storage,
                            'trace_wordstack': options.trace_wordstack,
                        }
                    ),
                )
            cut_point_rules = KEVMSemantics.cut_point_rules(
                options.break_on_jumpi,
                options.break_on_calls,
                options.break_on_storage,
                options.break_on_basic_blocks,
            )
            if options.break_on_cheatcodes:
                cut_point_rules.extend(
                    rule.label for rule in foundry.kevm.definition.all_modules_dict['FOUNDRY-CHEAT-CODES'].rules
                )
            run_prover(
                proof,
                create_kcfg_explore=create_kcfg_explore,
                max_depth=options.max_depth,
                max_iterations=options.max_iterations,
                cut_point_rules=cut_point_rules,
                terminal_rules=KEVMSemantics.terminal_rules(options.break_every_step),
                counterexample_info=options.counterexample_info,
                max_frontier_parallel=options.max_frontier_parallel,
                fail_fast=options.fail_fast,
            )

            if options.minimize_proofs or options.config_type == ConfigType.SUMMARY_CONFIG:
                proof.minimize_kcfg()

            if start_time is not None:
                end_time = time.time()
                proof.add_exec_time(end_time - start_time)
            proof.write_proof_data()

            # Only return the failure info to avoid pickling the whole proof
            if proof.failure_info is not None and not isinstance(proof.failure_info, APRFailureInfo):
                raise RuntimeError('Generated failure info for APRProof is not APRFailureInfo.')
            if proof.error_info is not None:
                return proof.error_info
            else:
                return proof.failure_info

    failure_infos: list[APRFailureInfo | Exception | None]
    if options.workers > 1:
        with ProcessPool(ncpus=options.workers) as process_pool:
            failure_infos = process_pool.map(init_and_run_proof, tests)
    else:
        failure_infos = []
        for test in tests:
            failure_infos.append(init_and_run_proof(test))

    proofs = [foundry.get_apr_proof(test.id) for test in tests]

    # Reconstruct the proof from the subprocess
    for proof, failure_info in zip(proofs, failure_infos, strict=True):
        assert proof.failure_info is None  # Refactor once this fails
        assert proof.error_info is None
        if isinstance(failure_info, Exception):
            proof.error_info = failure_info
        elif isinstance(failure_info, APRFailureInfo):
            proof.failure_info = failure_info

    return proofs


def method_to_apr_proof(
    test: FoundryTest,
    foundry: Foundry,
    kcfg_explore: KCFGExplore,
    config_type: ConfigType,
    bmc_depth: int | None = None,
    run_constructor: bool = False,
    use_gas: bool = False,
    deployment_state_entries: Iterable[DeploymentStateEntry] | None = None,
    summary_ids: Iterable[str] = (),
    active_symbolik: bool = False,
    hevm: bool = False,
    trace_options: TraceOptions | None = None,
) -> APRProof:
    setup_proof = None
    setup_proof_is_constructor = False
    if isinstance(test.method, Contract.Constructor):
        _LOGGER.info(f'Creating proof from constructor for test: {test.id}')
    elif test.method.signature != 'setUp()' and 'setUp' in test.contract.method_by_name:
        _LOGGER.info(f'Using setUp method for test: {test.id}')
        setup_proof = _load_setup_proof(foundry, test.contract)
    elif run_constructor:
        _LOGGER.info(f'Using constructor final state as initial state for test: {test.id}')
        setup_proof = _load_constructor_proof(foundry, test.contract)
        setup_proof_is_constructor = True

    kcfg, init_node_id, target_node_id = _method_to_initialized_cfg(
        foundry=foundry,
        test=test,
        kcfg_explore=kcfg_explore,
        setup_proof=setup_proof,
        graft_setup_proof=((setup_proof is not None) and not setup_proof_is_constructor),
        use_gas=use_gas,
        deployment_state_entries=deployment_state_entries,
        active_symbolik=active_symbolik,
        hevm=hevm,
        trace_options=trace_options,
        config_type=config_type,
    )

    apr_proof = APRProof(
        test.id,
        kcfg,
        [],
        init_node_id,
        target_node_id,
        {},
        bmc_depth=bmc_depth,
        proof_dir=foundry.proofs_dir,
        subproof_ids=summary_ids,
    )

    return apr_proof


def _load_setup_proof(foundry: Foundry, contract: Contract) -> APRProof:
    latest_version = foundry.latest_proof_version(f'{contract.name_with_path}.setUp()')
    setup_digest = f'{contract.name_with_path}.setUp():{latest_version}'
    apr_proof = APRProof.read_proof_data(foundry.proofs_dir, setup_digest)
    return apr_proof


def _load_constructor_proof(foundry: Foundry, contract: Contract) -> APRProof:
    latest_version = foundry.latest_proof_version(f'{contract.name_with_path}.init')
    setup_digest = f'{contract.name_with_path}.init:{latest_version}'
    apr_proof = APRProof.read_proof_data(foundry.proofs_dir, setup_digest)
    return apr_proof


def _method_to_initialized_cfg(
    foundry: Foundry,
    test: FoundryTest,
    kcfg_explore: KCFGExplore,
    config_type: ConfigType,
    *,
    setup_proof: APRProof | None = None,
    graft_setup_proof: bool = False,
    use_gas: bool = False,
    deployment_state_entries: Iterable[DeploymentStateEntry] | None = None,
    active_symbolik: bool = False,
    hevm: bool = False,
    trace_options: TraceOptions | None = None,
) -> tuple[KCFG, int, int]:
    _LOGGER.info(f'Initializing KCFG for test: {test.id}')

    empty_config = foundry.kevm.definition.empty_config(GENERATED_TOP_CELL)
    kcfg, new_node_ids, init_node_id, target_node_id = _method_to_cfg(
        empty_config,
        test.contract,
        test.method,
        setup_proof,
        graft_setup_proof,
        use_gas,
        deployment_state_entries,
        active_symbolik,
        config_type=config_type,
        hevm=hevm,
        trace_options=trace_options,
    )

    for node_id in new_node_ids:
        _LOGGER.info(f'Expanding macros in node {node_id} for test: {test.name}')
        init_term = kcfg.node(node_id).cterm.kast
        init_term = KDefinition__expand_macros(foundry.kevm.definition, init_term)
        init_cterm = CTerm.from_kast(init_term)
        _LOGGER.info(f'Computing definedness constraint for node {node_id} for test: {test.name}')
        init_cterm = kcfg_explore.cterm_symbolic.assume_defined(init_cterm)
        kcfg.let_node(node_id, cterm=init_cterm)

    _LOGGER.info(f'Expanding macros in target state for test: {test.name}')
    target_term = kcfg.node(target_node_id).cterm.kast
    target_term = KDefinition__expand_macros(foundry.kevm.definition, target_term)
    target_cterm = CTerm.from_kast(target_term)
    kcfg.let_node(target_node_id, cterm=target_cterm)

    _LOGGER.info(f'Simplifying KCFG for test: {test.name}')
    kcfg_explore.simplify(kcfg, {})

    return kcfg, init_node_id, target_node_id


def _method_to_cfg(
    empty_config: KInner,
    contract: Contract,
    method: Contract.Method | Contract.Constructor,
    setup_proof: APRProof | None,
    graft_setup_proof: bool,
    use_gas: bool,
    deployment_state_entries: Iterable[DeploymentStateEntry] | None,
    active_symbolik: bool,
    config_type: ConfigType,
    hevm: bool = False,
    trace_options: TraceOptions | None = None,
) -> tuple[KCFG, list[int], int, int]:
    calldata = None
    callvalue = None

    contract_code = bytes.fromhex(contract.deployed_bytecode)
    if isinstance(method, Contract.Constructor):
        program = bytes.fromhex(contract.bytecode)
        callvalue = method.callvalue_cell

    elif isinstance(method, Contract.Method):
        calldata = method.calldata_cell(contract)
        callvalue = method.callvalue_cell
        program = contract_code

    init_cterm = _init_cterm(
        empty_config,
        program=program,
        contract_code=bytesToken(contract_code),
        use_gas=use_gas,
        deployment_state_entries=deployment_state_entries,
        calldata=calldata,
        callvalue=callvalue,
        is_constructor=isinstance(method, Contract.Constructor),
        active_symbolik=active_symbolik,
        trace_options=trace_options,
        config_type=config_type,
    )
    new_node_ids = []

    if setup_proof:
        if setup_proof.pending:
            raise RuntimeError(
                f'Initial state proof {setup_proof.id} for {contract.name_with_path}.{method.signature} still has pending branches.'
            )

        if setup_proof.failing:
            raise RuntimeError(
                f'Initial state proof {setup_proof.id} for {contract.name_with_path}.{method.signature} still has failing branches.'
            )

        assert setup_proof.status == ProofStatus.PASSED

        init_node_id = setup_proof.init
        # Copy KCFG and minimize it
        if graft_setup_proof:
            cfg = KCFG.from_dict(setup_proof.kcfg.to_dict())
            cfg.minimize()
            cfg.remove_node(setup_proof.target)
        else:
            cfg = KCFG()
        final_states = [cover.source for cover in setup_proof.kcfg.covers(target_id=setup_proof.target)]
        if not final_states:
            _LOGGER.warning(
                f'Initial state proof {setup_proof.id} for {contract.name_with_path}.{method.signature} has no passing branches to build on. Method will not be executed.'
            )

        for final_node in final_states:
            new_init_cterm = _update_cterm_from_node(init_cterm, final_node, config_type)
            new_node = cfg.create_node(new_init_cterm)
            if graft_setup_proof:
                cfg.create_edge(final_node.id, new_node.id, depth=1)
            elif len(final_states) != 1:
                raise RuntimeError(
                    f'KCFG grafting must be enabled for branching proofs. Proof {setup_proof.id} branched.'
                )
            new_node_ids.append(new_node.id)
    else:
        cfg = KCFG()
        init_node = cfg.create_node(init_cterm)
        new_node_ids = [init_node.id]
        init_node_id = init_node.id

    final_cterm = _final_cterm(
        empty_config,
        program=bytesToken(contract_code),
        failing=method.is_testfail,
        config_type=config_type,
        is_test=method.is_test,
        hevm=hevm,
    )
    target_node = cfg.create_node(final_cterm)

    return cfg, new_node_ids, init_node_id, target_node.id


def _update_cterm_from_node(cterm: CTerm, node: KCFG.Node, config_type: ConfigType) -> CTerm:
    new_accounts_cell = node.cterm.cell('ACCOUNTS_CELL')
    number_cell = node.cterm.cell('NUMBER_CELL')
    timestamp_cell = node.cterm.cell('TIMESTAMP_CELL')
    basefee_cell = node.cterm.cell('BASEFEE_CELL')
    chainid_cell = node.cterm.cell('CHAINID_CELL')
    coinbase_cell = node.cterm.cell('COINBASE_CELL')
    prevcaller_cell = node.cterm.cell('PREVCALLER_CELL')
    prevorigin_cell = node.cterm.cell('PREVORIGIN_CELL')
    newcaller_cell = node.cterm.cell('NEWCALLER_CELL')
    neworigin_cell = node.cterm.cell('NEWORIGIN_CELL')
    active_cell = node.cterm.cell('ACTIVE_CELL')
    depth_cell = node.cterm.cell('DEPTH_CELL')
    singlecall_cell = node.cterm.cell('SINGLECALL_CELL')
    gas_cell = node.cterm.cell('GAS_CELL')
    callgas_cell = node.cterm.cell('CALLGAS_CELL')

    all_accounts = flatten_label('_AccountCellMap_', new_accounts_cell)

    new_accounts = [CTerm(account, []) for account in all_accounts if (type(account) is KApply and account.is_cell)]
    non_cell_accounts = [account for account in all_accounts if not (type(account) is KApply and account.is_cell)]

    new_accounts_map = {account.cell('ACCTID_CELL'): account for account in new_accounts}

    if config_type == ConfigType.SUMMARY_CONFIG:
        for account_id, account in new_accounts_map.items():
            acct_id_cell = account.cell('ACCTID_CELL')
            if type(acct_id_cell) is KVariable:
                acct_id = acct_id_cell.name
            elif type(acct_id_cell) is KToken:
                acct_id = acct_id_cell.token
            else:
                raise RuntimeError(
                    f'Failed to abstract storage. acctId cell is neither variable nor token: {acct_id_cell}'
                )
            new_accounts_map[account_id] = CTerm(
                set_cell(
                    account.config,
                    'STORAGE_CELL',
                    KVariable(f'STORAGE_{acct_id}', sort=KSort('Map')),
                ),
                [],
            )

    new_accounts_cell = KEVM.accounts([account.config for account in new_accounts_map.values()] + non_cell_accounts)

    new_init_cterm = CTerm(set_cell(cterm.config, 'ACCOUNTS_CELL', new_accounts_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'NUMBER_CELL', number_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'TIMESTAMP_CELL', timestamp_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'BASEFEE_CELL', basefee_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'CHAINID_CELL', chainid_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'COINBASE_CELL', coinbase_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'PREVCALLER_CELL', prevcaller_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'PREVORIGIN_CELL', prevorigin_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'NEWCALLER_CELL', newcaller_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'NEWORIGIN_CELL', neworigin_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'ACTIVE_CELL', active_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'DEPTH_CELL', depth_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'SINGLECALL_CELL', singlecall_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'GAS_CELL', gas_cell), [])
    new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'CALLGAS_CELL', callgas_cell), [])

    # Adding constraints from the initial cterm and initial node
    for constraint in cterm.constraints + node.cterm.constraints:
        new_init_cterm = new_init_cterm.add_constraint(constraint)
    new_init_cterm = KEVM.add_invariant(new_init_cterm)

    new_init_cterm = new_init_cterm.remove_useless_constraints()

    return new_init_cterm


def deployment_state_to_account_cells(deployment_state_entries: Iterable[DeploymentStateEntry]) -> list[KApply]:
    accounts = _process_deployment_state(deployment_state_entries)
    address_list = accounts.keys()
    k_accounts = []
    for addr in address_list:
        k_accounts.append(
            KEVM.account_cell(
                intToken(addr),
                intToken(accounts[addr]['balance']),
                KEVM.parse_bytestack(stringToken(accounts[addr]['code'])),
                map_of(accounts[addr]['storage']),
                map_empty(),
                intToken(accounts[addr]['nonce']),
            )
        )
    return k_accounts


def _process_deployment_state(deployment_state: Iterable[DeploymentStateEntry]) -> dict:
    accounts: dict[int, dict] = {}

    def _init_account(address: int) -> None:
        if address not in accounts.keys():
            accounts[address] = {'balance': 0, 'nonce': 0, 'code': '', 'storage': {}}

    for entry in deployment_state:
        if entry.has_ignored_kind or entry.reverted:
            continue

        _addr = hex_string_to_int(entry.account)

        if entry.is_create:
            _init_account(_addr)
            accounts[_addr]['code'] = entry.deployed_code

        if entry.updates_balance:
            _init_account(_addr)
            accounts[_addr]['balance'] = entry.new_balance

        for update in entry.storage_updates:
            _int_address = hex_string_to_int(update.address)
            _init_account(_int_address)
            accounts[_int_address]['storage'][intToken(hex_string_to_int(update.slot))] = intToken(
                hex_string_to_int(update.value)
            )

    return accounts


def _init_cterm(
    empty_config: KInner,
    program: bytes,
    contract_code: KInner,
    use_gas: bool,
    config_type: ConfigType,
    active_symbolik: bool,
    is_constructor: bool,
    *,
    calldata: KInner | None = None,
    callvalue: KInner | None = None,
    deployment_state_entries: Iterable[DeploymentStateEntry] | None = None,
    trace_options: TraceOptions | None = None,
) -> CTerm:
    schedule = KApply('SHANGHAI_EVM')

    if not trace_options:
        trace_options = TraceOptions({})

    jumpdests = set_of(_process_jumpdests(bytecode=program, offset=0))
    init_subst = {
        'MODE_CELL': KApply('NORMAL'),
        'USEGAS_CELL': TRUE if use_gas else FALSE,
        'SCHEDULE_CELL': schedule,
        'STATUSCODE_CELL': KVariable('STATUSCODE'),
        'PROGRAM_CELL': bytesToken(program),
        'JUMPDESTS_CELL': jumpdests,
        'ID_CELL': KVariable(Foundry.symbolic_contract_id(), sort=KSort('Int')),
        'ORIGIN_CELL': KVariable('ORIGIN_ID', sort=KSort('Int')),
        'CALLER_CELL': KVariable('CALLER_ID', sort=KSort('Int')),
        'LOCALMEM_CELL': bytesToken(b''),
        'ACTIVE_CELL': FALSE,
        'MEMORYUSED_CELL': intToken(0),
        'WORDSTACK_CELL': KApply('.WordStack_EVM-TYPES_WordStack'),
        'PC_CELL': intToken(0),
        'GAS_CELL': KEVM.inf_gas(KVariable('VGAS')),
        'K_CELL': KSequence([KEVM.sharp_execute(), KVariable('CONTINUATION')]),
        'SINGLECALL_CELL': FALSE,
        'ISREVERTEXPECTED_CELL': FALSE,
        'ISOPCODEEXPECTED_CELL': FALSE,
        'RECORDEVENT_CELL': FALSE,
        'ISEVENTEXPECTED_CELL': FALSE,
        'ISCALLWHITELISTACTIVE_CELL': FALSE,
        'ISSTORAGEWHITELISTACTIVE_CELL': FALSE,
        'ADDRESSSET_CELL': set_empty(),
        'STORAGESLOTSET_CELL': set_empty(),
        'MOCKCALLS_CELL': KApply('.MockCallCellMap'),
        'ACTIVETRACING_CELL': TRUE if trace_options.active_tracing else FALSE,
        'TRACESTORAGE_CELL': TRUE if trace_options.trace_storage else FALSE,
        'TRACEWORDSTACK_CELL': TRUE if trace_options.trace_wordstack else FALSE,
        'TRACEMEMORY_CELL': TRUE if trace_options.trace_memory else FALSE,
        'RECORDEDTRACE_CELL': FALSE,
        'TRACEDATA_CELL': KApply('.List'),
    }

    if config_type == ConfigType.TEST_CONFIG or active_symbolik:
        init_account_list = _create_initial_account_list(contract_code, deployment_state_entries)
        init_subst_test = {
            'OUTPUT_CELL': bytesToken(b''),
            'CALLSTACK_CELL': list_empty(),
            'CALLDEPTH_CELL': intToken(0),
            'ID_CELL': Foundry.address_TEST_CONTRACT(),
            'LOG_CELL': list_empty(),
            'ACCESSEDACCOUNTS_CELL': set_empty(),
            'ACCESSEDSTORAGE_CELL': map_empty(),
            'INTERIMSTATES_CELL': list_empty(),
            'TOUCHEDACCOUNTS_CELL': set_empty(),
            'STATIC_CELL': FALSE,
            'ACCOUNTS_CELL': KEVM.accounts(init_account_list),
        }
        init_subst.update(init_subst_test)
    else:
        # Symbolic accounts of all relevant contracts
        # Status: Currently, only the executing contract
        # TODO: Add all other accounts belonging to relevant contracts
        accounts: list[KInner] = [
            Foundry.symbolic_account(Foundry.symbolic_contract_prefix(), contract_code),
            KVariable('ACCOUNTS_REST', sort=KSort('AccountCellMap')),
        ]

        init_subst_accounts = {'ACCOUNTS_CELL': KEVM.accounts(accounts)}
        init_subst.update(init_subst_accounts)

    if calldata is not None:
        init_subst['CALLDATA_CELL'] = calldata

    if callvalue is not None:
        init_subst['CALLVALUE_CELL'] = callvalue

    if not use_gas:
        init_subst['GAS_CELL'] = intToken(0)
        init_subst['CALLGAS_CELL'] = intToken(0)
        init_subst['REFUND_CELL'] = intToken(0)

    # constructor can not be called in a static context.
    if is_constructor:
        init_subst['STATIC_CELL'] = FALSE

    init_term = Subst(init_subst)(empty_config)
    init_cterm = CTerm.from_kast(init_term)
    for contract_id in [Foundry.symbolic_contract_id(), 'CALLER_ID', 'ORIGIN_ID']:
        # The address of the executing contract, the calling contract, and the origin contract
        # is always guaranteed to not be the address of the cheatcode contract
        init_cterm = init_cterm.add_constraint(
            mlEqualsFalse(KApply('_==Int_', [KVariable(contract_id, sort=KSort('Int')), Foundry.address_CHEATCODE()]))
        )

    # The calling contract is assumed to be in the present accounts for non-tests
    if not (config_type == ConfigType.TEST_CONFIG or active_symbolik):
        init_cterm.add_constraint(
            mlEqualsTrue(
                KApply(
                    '_in_keys(_)_MAP_Bool_KItem_Map',
                    [KVariable('CALLER_ID', sort=KSort('Int')), init_cterm.cell('ACCOUNTS_CELL')],
                )
            )
        )

    init_cterm = KEVM.add_invariant(init_cterm)

    return init_cterm


def _create_initial_account_list(
    program: KInner, deployment_state: Iterable[DeploymentStateEntry] | None
) -> list[KInner]:
    _contract = KEVM.account_cell(
        Foundry.address_TEST_CONTRACT(),
        intToken(0),
        program,
        map_empty(),
        map_empty(),
        intToken(1),
    )
    init_account_list: list[KInner] = [
        _contract,
        Foundry.account_CHEATCODE_ADDRESS(map_empty()),
    ]
    if deployment_state is not None:
        init_account_list.extend(deployment_state_to_account_cells(deployment_state))

    return init_account_list


def _final_cterm(
    empty_config: KInner,
    program: KInner,
    config_type: ConfigType,
    *,
    failing: bool,
    is_test: bool = True,
    hevm: bool = False,
) -> CTerm:
    final_term = _final_term(empty_config, program, config_type=config_type)
    dst_failed_post = KEVM.lookup(KVariable('CHEATCODE_STORAGE_FINAL'), Foundry.loc_FOUNDRY_FAILED())
    final_cterm = CTerm.from_kast(final_term)
    if is_test:
        if not hevm:
            foundry_success = Foundry.success(
                KVariable('STATUSCODE_FINAL'),
                dst_failed_post,
                KVariable('ISREVERTEXPECTED_FINAL'),
                KVariable('ISOPCODEEXPECTED_FINAL'),
                KVariable('RECORDEVENT_FINAL'),
                KVariable('ISEVENTEXPECTED_FINAL'),
            )
            if not failing:
                return final_cterm.add_constraint(mlEqualsTrue(foundry_success))
            else:
                return final_cterm.add_constraint(mlEqualsTrue(notBool(foundry_success)))
        else:
            if not failing:
                return final_cterm.add_constraint(
                    mlEqualsTrue(
                        Hevm.hevm_success(KVariable('STATUSCODE_FINAL'), dst_failed_post, KVariable('OUTPUT_FINAL'))
                    )
                )
            else:
                # To do: Print warning to the user
                return final_cterm.add_constraint(
                    mlEqualsTrue(Hevm.hevm_fail(KVariable('STATUSCODE_FINAL'), dst_failed_post))
                )

    return final_cterm


def _final_term(empty_config: KInner, program: KInner, config_type: ConfigType) -> KInner:
    post_account_cell = KEVM.account_cell(
        Foundry.address_TEST_CONTRACT(),
        KVariable('ACCT_BALANCE_FINAL'),
        program,
        KVariable('ACCT_STORAGE_FINAL'),
        KVariable('ACCT_ORIGSTORAGE_FINAL'),
        KVariable('ACCT_NONCE_FINAL'),
    )
    final_subst = {
        'K_CELL': KSequence([KEVM.halt(), KVariable('CONTINUATION')]),
        'STATUSCODE_CELL': KVariable('STATUSCODE_FINAL'),
        'OUTPUT_CELL': KVariable('OUTPUT_FINAL'),
        'ISREVERTEXPECTED_CELL': KVariable('ISREVERTEXPECTED_FINAL'),
        'ISOPCODEEXPECTED_CELL': KVariable('ISOPCODEEXPECTED_FINAL'),
        'RECORDEVENT_CELL': KVariable('RECORDEVENT_FINAL'),
        'ISEVENTEXPECTED_CELL': KVariable('ISEVENTEXPECTED_FINAL'),
        'ISCALLWHITELISTACTIVE_CELL': KVariable('ISCALLWHITELISTACTIVE_FINAL'),
        'ISSTORAGEWHITELISTACTIVE_CELL': KVariable('ISSTORAGEWHITELISTACTIVE_FINAL'),
        'ADDRESSSET_CELL': KVariable('ADDRESSSET_FINAL'),
        'STORAGESLOTSET_CELL': KVariable('STORAGESLOTSET_FINAL'),
    }

    if config_type == ConfigType.TEST_CONFIG:
        final_subst_test = {
            'ID_CELL': Foundry.address_TEST_CONTRACT(),
            'ACCOUNTS_CELL': KEVM.accounts(
                [
                    post_account_cell,  # test contract address
                    Foundry.account_CHEATCODE_ADDRESS(KVariable('CHEATCODE_STORAGE_FINAL')),
                    KVariable('ACCOUNTS_FINAL'),
                ]
            ),
        }
        final_subst.update(final_subst_test)

    return abstract_cell_vars(
        Subst(final_subst)(empty_config),
        [
            KVariable('STATUSCODE_FINAL'),
            KVariable('ACCOUNTS_FINAL'),
            KVariable('OUTPUT_FINAL'),
            KVariable('ISREVERTEXPECTED_FINAL'),
            KVariable('ISOPCODEEXPECTED_FINAL'),
            KVariable('RECORDEVENT_FINAL'),
            KVariable('ISEVENTEXPECTED_FINAL'),
            KVariable('ISCALLWHITELISTACTIVE_FINAL'),
            KVariable('ISSTORAGEWHITELISTACTIVE_FINAL'),
            KVariable('ADDRESSSET_FINAL'),
            KVariable('STORAGESLOTSET_FINAL'),
        ],
    )
