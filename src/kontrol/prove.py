from __future__ import annotations

import logging
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, NamedTuple

from kevm_pyk.kevm import KEVM, KEVMSemantics
from kevm_pyk.utils import KDefinition__expand_macros, abstract_cell_vars, legacy_explore, run_prover
from pathos.pools import ProcessPool  # type: ignore
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KSequence, KSort, KVariable, Subst
from pyk.kast.manip import flatten_label, set_cell
from pyk.kcfg import KCFG
from pyk.prelude.bytes import bytesToken
from pyk.prelude.collections import list_empty, map_empty, map_of, set_empty
from pyk.prelude.k import GENERATED_TOP_CELL
from pyk.prelude.kbool import FALSE, TRUE, notBool
from pyk.prelude.kint import intToken
from pyk.prelude.ml import mlEqualsTrue
from pyk.prelude.string import stringToken
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRBMCProof, APRProof
from pyk.utils import run_process, unique

from .foundry import Foundry
from .solc_to_k import Contract, hex_string_to_int

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Final

    from pyk.kast.inner import KInner
    from pyk.kcfg import KCFGExplore
    from pyk.proof.reachability import APRFailureInfo

    from .deployment import SummaryEntry
    from .options import ProveOptions, RPCOptions

_LOGGER: Final = logging.getLogger(__name__)


def foundry_prove(
    foundry: Foundry,
    prove_options: ProveOptions,
    rpc_options: RPCOptions,
    tests: Iterable[tuple[str, int | None]] = (),
    include_summaries: Iterable[tuple[str, int | None]] = (),
) -> list[APRProof]:
    if prove_options.workers <= 0:
        raise ValueError(f'Must have at least one worker, found: --workers {prove_options.workers}')
    if prove_options.max_iterations is not None and prove_options.max_iterations < 0:
        raise ValueError(
            f'Must have a non-negative number of iterations, found: --max-iterations {prove_options.max_iterations}'
        )

    if rpc_options.use_booster:
        try:
            run_process(('which', 'kore-rpc-booster'), pipe_stderr=True).stdout.strip()
        except CalledProcessError:
            raise RuntimeError(
                "Couldn't locate the kore-rpc-booster RPC binary. Please put 'kore-rpc-booster' on PATH manually or using kup install/kup shell."
            ) from None

    foundry.mk_proofs_dir()

    summary_ids: list[str] = []
    if prove_options.cse:
        test_suite = collect_tests(foundry, tests, reinit=prove_options.reinit, return_empty=True)
        for test in test_suite:
            if not isinstance(test.method, Contract.Method) or test.method.function_calls is None:
                continue

            test_version_tuples = [parse_test_version_tuple(t) for t in test.method.function_calls]

            if len(test_version_tuples) > 0:
                print(f'For test {test.name}, found external calls: {test_version_tuples}')
                summary_ids.extend(
                    p.id for p in foundry_prove(foundry, prove_options, rpc_options, test_version_tuples)
                )

    test_suite = collect_tests(foundry, tests, reinit=prove_options.reinit)
    test_names = [test.name for test in test_suite]
    print(f'Running functions: {test_names}')

    contracts = [test.contract for test in test_suite]
    setup_method_tests = collect_setup_methods(foundry, contracts, reinit=prove_options.reinit)
    setup_method_names = [test.name for test in setup_method_tests]

    constructor_tests = collect_constructors(foundry, contracts, reinit=prove_options.reinit)
    constructor_names = [test.name for test in constructor_tests]

    _LOGGER.info(f'Running tests: {test_names}')

    _LOGGER.info(f'Updating digests: {test_names}')
    for test in test_suite:
        test.method.update_digest(foundry.digest_file)

    _LOGGER.info(f'Updating digests: {setup_method_names}')
    for test in setup_method_tests:
        test.method.update_digest(foundry.digest_file)

    _LOGGER.info(f'Updating digests: {constructor_names}')
    for test in constructor_tests:
        test.method.update_digest(foundry.digest_file)

    def _run_prover(_test_suite: list[FoundryTest], include_summaries: bool = False) -> list[APRProof]:
        return _run_cfg_group(
            tests=_test_suite,
            foundry=foundry,
            prove_options=prove_options,
            rpc_options=rpc_options,
            summary_ids=(summary_ids if include_summaries else []),
        )

    if prove_options.run_constructor:
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
    return results


def parse_test_version_tuple(value: str) -> tuple[str, int | None]:
    if ':' in value:
        test, version = value.split(':')
        return (test, int(version))
    else:
        return (value, None)


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
    foundry: Foundry, tests: Iterable[tuple[str, int | None]] = (), *, reinit: bool, return_empty: bool = False
) -> list[FoundryTest]:
    if not tests and not return_empty:
        tests = [(test, None) for test in foundry.all_tests]
    matching_tests = []
    for test, version in tests:
        matching_tests += [(sig, version) for sig in foundry.matching_sigs(test)]
    tests = list(unique(matching_tests))

    res: list[FoundryTest] = []
    for sig, ver in tests:
        contract, method = foundry.get_contract_and_method(sig)
        version = foundry.resolve_proof_version(sig, reinit, ver)
        res.append(FoundryTest(contract, method, version))
    return res


def collect_setup_methods(foundry: Foundry, contracts: Iterable[Contract] = (), *, reinit: bool) -> list[FoundryTest]:
    res: list[FoundryTest] = []
    contract_names: set[str] = set()  # ensures uniqueness of each result (Contract itself is not hashable)
    for contract in contracts:
        if contract.name_with_path in contract_names:
            continue
        contract_names.add(contract.name_with_path)

        method = contract.method_by_name.get('setUp')
        if not method:
            continue
        version = foundry.resolve_proof_version(f'{contract.name_with_path}.setUp()', reinit, None)
        res.append(FoundryTest(contract, method, version))
    return res


def collect_constructors(foundry: Foundry, contracts: Iterable[Contract] = (), *, reinit: bool) -> list[FoundryTest]:
    res: list[FoundryTest] = []
    contract_names: set[str] = set()  # ensures uniqueness of each result (Contract itself is not hashable)
    for contract in contracts:
        if contract.name_with_path in contract_names:
            continue
        contract_names.add(contract.name_with_path)

        method = contract.constructor
        if not method:
            continue
        version = foundry.resolve_proof_version(f'{contract.name_with_path}.init', reinit, None)
        res.append(FoundryTest(contract, method, version))
    return res


def _run_cfg_group(
    tests: list[FoundryTest],
    foundry: Foundry,
    prove_options: ProveOptions,
    rpc_options: RPCOptions,
    summary_ids: Iterable[str],
) -> list[APRProof]:
    def init_and_run_proof(test: FoundryTest) -> APRFailureInfo | None:
        if Proof.proof_data_exists(test.id, foundry.proofs_dir):
            apr_proof = foundry.get_apr_proof(test.id)
            if apr_proof.passed:
                return None
        start_server = rpc_options.port is None
        with legacy_explore(
            foundry.kevm,
            kcfg_semantics=KEVMSemantics(auto_abstract_gas=prove_options.auto_abstract_gas),
            id=test.id,
            bug_report=prove_options.bug_report,
            kore_rpc_command=rpc_options.kore_rpc_command,
            llvm_definition_dir=foundry.llvm_library if rpc_options.use_booster else None,
            smt_timeout=rpc_options.smt_timeout,
            smt_retry_limit=rpc_options.smt_retry_limit,
            trace_rewrites=rpc_options.trace_rewrites,
            start_server=start_server,
            port=rpc_options.port,
            maude_port=rpc_options.maude_port,
        ) as kcfg_explore:
            proof = method_to_apr_proof(
                test=test,
                foundry=foundry,
                kcfg_explore=kcfg_explore,
                bmc_depth=prove_options.bmc_depth,
                run_constructor=prove_options.run_constructor,
                use_gas=prove_options.use_gas,
                summary_entries=prove_options.summary_entries,
                summary_ids=summary_ids,
            )

            cut_point_rules = KEVMSemantics.cut_point_rules(
                prove_options.break_on_jumpi,
                prove_options.break_on_calls,
                prove_options.break_on_storage,
                prove_options.break_on_basic_blocks,
            )
            if prove_options.break_on_cheatcodes:
                cut_point_rules.extend(
                    rule.label for rule in foundry.kevm.definition.all_modules_dict['FOUNDRY-CHEAT-CODES'].rules
                )

            run_prover(
                foundry.kevm,
                proof,
                kcfg_explore,
                max_depth=prove_options.max_depth,
                max_iterations=prove_options.max_iterations,
                cut_point_rules=cut_point_rules,
                terminal_rules=KEVMSemantics.terminal_rules(prove_options.break_every_step),
                counterexample_info=prove_options.counterexample_info,
            )

            # Only return the failure info to avoid pickling the whole proof
            return proof.failure_info

    failure_infos: list[APRFailureInfo | None]
    if prove_options.workers > 1:
        with ProcessPool(ncpus=prove_options.workers) as process_pool:
            failure_infos = process_pool.map(init_and_run_proof, tests)
    else:
        failure_infos = []
        for test in tests:
            failure_infos.append(init_and_run_proof(test))

    proofs = [foundry.get_apr_proof(test.id) for test in tests]

    # Reconstruct the proof from the subprocess
    for proof, failure_info in zip(proofs, failure_infos, strict=True):
        assert proof.failure_info is None  # Refactor once this fails
        proof.failure_info = failure_info

    return proofs


def method_to_apr_proof(
    test: FoundryTest,
    foundry: Foundry,
    kcfg_explore: KCFGExplore,
    bmc_depth: int | None = None,
    run_constructor: bool = False,
    use_gas: bool = False,
    summary_entries: Iterable[SummaryEntry] | None = None,
    summary_ids: Iterable[str] = (),
) -> APRProof:
    if Proof.proof_data_exists(test.id, foundry.proofs_dir):
        apr_proof = foundry.get_apr_proof(test.id)
        apr_proof.write_proof_data()
        return apr_proof

    setup_proof = None
    if isinstance(test.method, Contract.Constructor):
        _LOGGER.info(f'Creating proof from constructor for test: {test.id}')
    elif test.method.signature != 'setUp()' and 'setUp' in test.contract.method_by_name:
        _LOGGER.info(f'Using setUp method for test: {test.id}')
        setup_proof = _load_setup_proof(foundry, test.contract)
    elif run_constructor:
        _LOGGER.info(f'Using constructor final state as initial state for test: {test.id}')
        setup_proof = _load_constructor_proof(foundry, test.contract)

    kcfg, init_node_id, target_node_id = _method_to_initialized_cfg(
        foundry=foundry,
        test=test,
        kcfg_explore=kcfg_explore,
        setup_proof=setup_proof,
        use_gas=use_gas,
        summary_entries=summary_entries,
    )

    if bmc_depth is not None:
        apr_proof = APRBMCProof(
            test.id,
            kcfg,
            [],
            init_node_id,
            target_node_id,
            {},
            bmc_depth,
            proof_dir=foundry.proofs_dir,
            subproof_ids=summary_ids,
        )
    else:
        apr_proof = APRProof(
            test.id, kcfg, [], init_node_id, target_node_id, {}, proof_dir=foundry.proofs_dir, subproof_ids=summary_ids
        )

    apr_proof.write_proof_data()
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
    *,
    setup_proof: APRProof | None = None,
    use_gas: bool = False,
    summary_entries: Iterable[SummaryEntry] | None = None,
) -> tuple[KCFG, int, int]:
    _LOGGER.info(f'Initializing KCFG for test: {test.id}')

    empty_config = foundry.kevm.definition.empty_config(GENERATED_TOP_CELL)
    kcfg, new_node_ids, init_node_id, target_node_id = _method_to_cfg(
        empty_config,
        test.contract,
        test.method,
        setup_proof,
        use_gas,
        summary_entries,
    )

    for node_id in new_node_ids:
        _LOGGER.info(f'Expanding macros in node {node_id} for test: {test.name}')
        init_term = kcfg.node(node_id).cterm.kast
        init_term = KDefinition__expand_macros(foundry.kevm.definition, init_term)
        init_cterm = CTerm.from_kast(init_term)
        _LOGGER.info(f'Computing definedness constraint for node {node_id} for test: {test.name}')
        init_cterm = kcfg_explore.cterm_assume_defined(init_cterm)
        kcfg.replace_node(node_id, init_cterm)

    _LOGGER.info(f'Expanding macros in target state for test: {test.name}')
    target_term = kcfg.node(target_node_id).cterm.kast
    target_term = KDefinition__expand_macros(foundry.kevm.definition, target_term)
    target_cterm = CTerm.from_kast(target_term)
    kcfg.replace_node(target_node_id, target_cterm)

    _LOGGER.info(f'Simplifying KCFG for test: {test.name}')
    kcfg_explore.simplify(kcfg, {})

    return kcfg, init_node_id, target_node_id


def _method_to_cfg(
    empty_config: KInner,
    contract: Contract,
    method: Contract.Method | Contract.Constructor,
    setup_proof: APRProof | None,
    use_gas: bool,
    summary_entries: Iterable[SummaryEntry] | None,
) -> tuple[KCFG, list[int], int, int]:
    calldata = None
    callvalue = None

    if isinstance(method, Contract.Constructor):
        program = KEVM.init_bytecode(KApply(f'contract_{contract.name_with_path}'))

    elif isinstance(method, Contract.Method):
        calldata = method.calldata_cell(contract)
        callvalue = method.callvalue_cell
        program = KEVM.bin_runtime(KApply(f'contract_{contract.name_with_path}'))

    init_cterm = _init_cterm(
        empty_config,
        program=program,
        use_gas=use_gas,
        summary_entries=summary_entries,
        is_test=method.is_test,
        is_setup=method.is_setup,
        calldata=calldata,
        callvalue=callvalue,
        is_constructor=isinstance(method, Contract.Constructor),
    )
    new_node_ids = []

    if setup_proof:
        if setup_proof.pending:
            raise RuntimeError(
                f'Initial state proof {setup_proof.id} for {contract.name_with_path}.{method.signature} still has pending branches.'
            )

        init_node_id = setup_proof.init

        cfg = KCFG.from_dict(setup_proof.kcfg.to_dict())  # Copy KCFG
        final_states = [cover.source for cover in cfg.covers(target_id=setup_proof.target)]
        cfg.remove_node(setup_proof.target)
        if not final_states:
            _LOGGER.warning(
                f'Initial state proof {setup_proof.id} for {contract.name_with_path}.{method.signature} has no passing branches to build on. Method will not be executed.'
            )
        for final_node in final_states:
            new_init_cterm = _update_cterm_from_node(init_cterm, final_node, contract.name_with_path)
            new_node = cfg.create_node(new_init_cterm)
            cfg.create_edge(final_node.id, new_node.id, depth=1)
            new_node_ids.append(new_node.id)
    else:
        cfg = KCFG()
        init_node = cfg.create_node(init_cterm)
        new_node_ids = [init_node.id]
        init_node_id = init_node.id

    final_cterm = _final_cterm(
        empty_config, program, failing=method.is_testfail, is_test=method.is_test, is_setup=method.is_setup
    )
    target_node = cfg.create_node(final_cterm)

    return cfg, new_node_ids, init_node_id, target_node.id


def _update_cterm_from_node(cterm: CTerm, node: KCFG.Node, contract_name: str) -> CTerm:
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
    new_accounts = [CTerm(account, []) for account in flatten_label('_AccountCellMap_', new_accounts_cell)]
    new_accounts_map = {account.cell('ACCTID_CELL'): account for account in new_accounts}
    test_contract_account = new_accounts_map[Foundry.address_TEST_CONTRACT()]

    new_accounts_map[Foundry.address_TEST_CONTRACT()] = CTerm(
        set_cell(
            test_contract_account.config,
            'CODE_CELL',
            KEVM.bin_runtime(KApply(f'contract_{contract_name}')),
        ),
        [],
    )

    new_accounts_cell = KEVM.accounts([account.config for account in new_accounts_map.values()])

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

    new_init_cterm = KEVM.add_invariant(new_init_cterm)

    return new_init_cterm


def summary_to_account_cells(summary_entries: Iterable[SummaryEntry]) -> list[KApply]:
    accounts = _process_summary(summary_entries)
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


def _process_summary(summary: Iterable[SummaryEntry]) -> dict:
    accounts: dict[int, dict] = {}

    def _init_account(address: int) -> None:
        if address not in accounts.keys():
            accounts[address] = {'balance': 0, 'nonce': 0, 'code': '', 'storage': {}}

    for entry in summary:
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
    program: KInner,
    use_gas: bool,
    is_test: bool,
    is_setup: bool,
    is_constructor: bool,
    *,
    calldata: KInner | None = None,
    callvalue: KInner | None = None,
    summary_entries: Iterable[SummaryEntry] | None = None,
) -> CTerm:
    schedule = KApply('SHANGHAI_EVM')

    init_subst = {
        'MODE_CELL': KApply('NORMAL'),
        'USEGAS_CELL': TRUE if use_gas else FALSE,
        'SCHEDULE_CELL': schedule,
        'STATUSCODE_CELL': KVariable('STATUSCODE'),
        'PROGRAM_CELL': program,
        'JUMPDESTS_CELL': KEVM.compute_valid_jumpdests(program),
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
    }

    if is_test or is_setup or is_constructor:
        init_account_list = _create_initial_account_list(program, summary_entries)
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

    if calldata is not None:
        init_subst['CALLDATA_CELL'] = calldata

    if callvalue is not None:
        init_subst['CALLVALUE_CELL'] = callvalue

    if not use_gas:
        init_subst['GAS_CELL'] = intToken(0)
        init_subst['CALLGAS_CELL'] = intToken(0)
        init_subst['REFUND_CELL'] = intToken(0)

    init_term = Subst(init_subst)(empty_config)
    init_cterm = CTerm.from_kast(init_term)
    init_cterm = KEVM.add_invariant(init_cterm)

    return init_cterm


def _create_initial_account_list(program: KInner, summary: Iterable[SummaryEntry] | None) -> list[KInner]:
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
    if summary is not None:
        init_account_list.extend(summary_to_account_cells(summary))

    return init_account_list


def _final_cterm(
    empty_config: KInner,
    program: KInner,
    *,
    failing: bool,
    is_test: bool = True,
    is_setup: bool = False,
) -> CTerm:
    final_term = _final_term(empty_config, program, is_test=is_test, is_setup=is_setup)
    dst_failed_post = KEVM.lookup(KVariable('CHEATCODE_STORAGE_FINAL'), Foundry.loc_FOUNDRY_FAILED())
    foundry_success = Foundry.success(
        KVariable('STATUSCODE_FINAL'),
        dst_failed_post,
        KVariable('ISREVERTEXPECTED_FINAL'),
        KVariable('ISOPCODEEXPECTED_FINAL'),
        KVariable('RECORDEVENT_FINAL'),
        KVariable('ISEVENTEXPECTED_FINAL'),
    )
    final_cterm = CTerm.from_kast(final_term)
    if is_test:
        if not failing:
            return final_cterm.add_constraint(mlEqualsTrue(foundry_success))
        else:
            return final_cterm.add_constraint(mlEqualsTrue(notBool(foundry_success)))
    return final_cterm


def _final_term(empty_config: KInner, program: KInner, is_test: bool, is_setup: bool) -> KInner:
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
        'ISREVERTEXPECTED_CELL': KVariable('ISREVERTEXPECTED_FINAL'),
        'ISOPCODEEXPECTED_CELL': KVariable('ISOPCODEEXPECTED_FINAL'),
        'RECORDEVENT_CELL': KVariable('RECORDEVENT_FINAL'),
        'ISEVENTEXPECTED_CELL': KVariable('ISEVENTEXPECTED_FINAL'),
        'ISCALLWHITELISTACTIVE_CELL': KVariable('ISCALLWHITELISTACTIVE_FINAL'),
        'ISSTORAGEWHITELISTACTIVE_CELL': KVariable('ISSTORAGEWHITELISTACTIVE_FINAL'),
        'ADDRESSSET_CELL': KVariable('ADDRESSSET_FINAL'),
        'STORAGESLOTSET_CELL': KVariable('STORAGESLOTSET_FINAL'),
    }

    if is_test or is_setup:
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
