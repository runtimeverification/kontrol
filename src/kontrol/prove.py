from __future__ import annotations

import logging
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, NamedTuple

from kevm_pyk.kevm import KEVM, KEVMSemantics
from kevm_pyk.utils import (
    KDefinition__expand_macros,
    abstract_cell_vars,
    constraints_for,
    kevm_prove,
    legacy_explore,
    print_failure_info,
)
from pathos.pools import ProcessPool  # type: ignore
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KSequence, KVariable, Subst
from pyk.kast.manip import flatten_label, free_vars, set_cell
from pyk.kcfg import KCFG
from pyk.prelude.k import GENERATED_TOP_CELL
from pyk.prelude.kbool import FALSE, notBool
from pyk.prelude.kint import intToken
from pyk.prelude.ml import mlEqualsTrue
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRBMCProof, APRProof
from pyk.utils import run_process, single, unique

from .foundry import Foundry

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
    from typing import Final

    from pyk.kast.inner import KInner
    from pyk.kcfg import KCFGExplore
    from pyk.kcfg.kcfg import NodeIdLike
    from pyk.utils import BugReport

    from .solc_to_k import Contract


_LOGGER: Final = logging.getLogger(__name__)


def foundry_prove(
    foundry_root: Path,
    max_depth: int = 1000,
    max_iterations: int | None = None,
    reinit: bool = False,
    tests: Iterable[tuple[str, int | None]] = (),
    exclude_tests: Iterable[str] = (),
    workers: int = 1,
    simplify_init: bool = True,
    break_every_step: bool = False,
    break_on_jumpi: bool = False,
    break_on_calls: bool = True,
    bmc_depth: int | None = None,
    bug_report: BugReport | None = None,
    kore_rpc_command: str | Iterable[str] | None = None,
    use_booster: bool = False,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    failure_info: bool = True,
    counterexample_info: bool = False,
    trace_rewrites: bool = False,
    auto_abstract_gas: bool = False,
    port: int | None = None,
) -> dict[tuple[str, int], tuple[bool, list[str] | None]]:
    if workers <= 0:
        raise ValueError(f'Must have at least one worker, found: --workers {workers}')
    if max_iterations is not None and max_iterations < 0:
        raise ValueError(f'Must have a non-negative number of iterations, found: --max-iterations {max_iterations}')

    if use_booster:
        try:
            run_process(('which', 'kore-rpc-booster'), pipe_stderr=True).stdout.strip()
        except CalledProcessError:
            raise RuntimeError(
                "Couldn't locate the kore-rpc-booster RPC binary. Please put 'kore-rpc-booster' on PATH manually or using kup install/kup shell."
            ) from None

    if kore_rpc_command is None:
        kore_rpc_command = ('kore-rpc-booster',) if use_booster else ('kore-rpc',)

    foundry = Foundry(foundry_root, bug_report=bug_report)
    foundry.mk_proofs_dir()

    test_suite = collect_tests(foundry, tests, reinit=reinit)
    test_names = [test.name for test in test_suite]
    tests_with_versions = [test.unparsed for test in test_suite]

    _LOGGER.info(f'Running tests: {test_names}')

    contracts = [test.contract for test in test_suite]
    _setup_methods = collect_setup_methods(foundry, contracts, reinit=reinit)
    setup_methods = [test.name for test in _setup_methods]
    setup_methods_with_versions = [test.unparsed for test in _setup_methods]

    _LOGGER.info(f'Updating digests: {[test_name for test_name, _ in tests]}')
    for test in test_suite:
        test.method.update_digest(foundry.digest_file)
    _LOGGER.info(f'Updating digests: {setup_methods}')
    for test in _setup_methods:
        test.method.update_digest(foundry.digest_file)

    _LOGGER.info(f'Running setup functions in parallel: {list(setup_methods)}')
    results = _run_cfg_group(
        setup_methods_with_versions,
        foundry,
        max_depth=max_depth,
        max_iterations=max_iterations,
        workers=workers,
        simplify_init=simplify_init,
        break_every_step=break_every_step,
        break_on_jumpi=break_on_jumpi,
        break_on_calls=break_on_calls,
        bmc_depth=bmc_depth,
        bug_report=bug_report,
        kore_rpc_command=kore_rpc_command,
        use_booster=use_booster,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        counterexample_info=counterexample_info,
        trace_rewrites=trace_rewrites,
        auto_abstract_gas=auto_abstract_gas,
        port=port,
    )
    failed = [setup_cfg for setup_cfg, passed in results.items() if not passed]
    if failed:
        raise ValueError(f'Running setUp method failed for {len(failed)} contracts: {failed}')

    _LOGGER.info(f'Running test functions in parallel: {test_names}')
    results = _run_cfg_group(
        tests_with_versions,
        foundry,
        max_depth=max_depth,
        max_iterations=max_iterations,
        workers=workers,
        simplify_init=simplify_init,
        break_every_step=break_every_step,
        break_on_jumpi=break_on_jumpi,
        break_on_calls=break_on_calls,
        bmc_depth=bmc_depth,
        bug_report=bug_report,
        kore_rpc_command=kore_rpc_command,
        use_booster=use_booster,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        counterexample_info=counterexample_info,
        trace_rewrites=trace_rewrites,
        auto_abstract_gas=auto_abstract_gas,
        port=port,
    )
    return results


class FoundryTest(NamedTuple):
    contract: Contract
    method: Contract.Method
    version: int

    @property
    def name(self) -> str:
        return f'{self.contract.name}.{self.method.signature}'

    @property
    def id(self) -> str:
        return f'{self.name}:{self.version}'

    @property
    def unparsed(self) -> tuple[str, int]:
        return self.name, self.version


def collect_tests(foundry: Foundry, tests: Iterable[tuple[str, int | None]] = (), *, reinit: bool) -> list[FoundryTest]:
    if not tests:
        tests = [(test, None) for test in foundry.all_tests]
    tests = list(unique((foundry.matching_sig(test), version) for test, version in tests))

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
        if contract.name in contract_names:
            continue
        contract_names.add(contract.name)

        method = contract.method_by_name.get('setUp')
        if not method:
            continue
        version = foundry.resolve_proof_version(f'{contract.name}.setUp()', reinit, None)
        res.append(FoundryTest(contract, method, version))
    return res


def _run_cfg_group(
    tests: list[tuple[str, int]],
    foundry: Foundry,
    *,
    max_depth: int,
    max_iterations: int | None,
    workers: int,
    simplify_init: bool,
    break_every_step: bool,
    break_on_jumpi: bool,
    break_on_calls: bool,
    bmc_depth: int | None,
    bug_report: BugReport | None,
    kore_rpc_command: str | Iterable[str] | None,
    use_booster: bool,
    smt_timeout: int | None,
    smt_retry_limit: int | None,
    counterexample_info: bool,
    trace_rewrites: bool,
    auto_abstract_gas: bool,
    port: int | None,
) -> dict[tuple[str, int], tuple[bool, list[str] | None]]:
    def init_and_run_proof(_init_problem: tuple[str, str, int]) -> tuple[bool, list[str] | None]:
        contract_name, method_sig, version = _init_problem
        contract = foundry.contracts[contract_name]
        method = contract.method_by_sig[method_sig]
        test_id = f'{contract_name}.{method_sig}:{version}'
        llvm_definition_dir = foundry.llvm_library if use_booster else None

        start_server = port is None

        with legacy_explore(
            foundry.kevm,
            kcfg_semantics=KEVMSemantics(auto_abstract_gas=auto_abstract_gas),
            id=test_id,
            bug_report=bug_report,
            kore_rpc_command=kore_rpc_command,
            llvm_definition_dir=llvm_definition_dir,
            smt_timeout=smt_timeout,
            smt_retry_limit=smt_retry_limit,
            trace_rewrites=trace_rewrites,
            start_server=start_server,
            port=port,
        ) as kcfg_explore:
            proof = method_to_apr_proof(
                foundry,
                contract,
                method,
                foundry.proofs_dir,
                kcfg_explore,
                test_id,
                simplify_init=simplify_init,
                bmc_depth=bmc_depth,
            )

            passed = kevm_prove(
                foundry.kevm,
                proof,
                kcfg_explore,
                max_depth=max_depth,
                max_iterations=max_iterations,
                break_every_step=break_every_step,
                break_on_jumpi=break_on_jumpi,
                break_on_calls=break_on_calls,
            )
            failure_log = None
            if not passed:
                failure_log = print_failure_info(proof, kcfg_explore, counterexample_info)
            return passed, failure_log

    def _split_test(test: tuple[str, int]) -> tuple[str, str, int]:
        test_name, version = test
        contract, method = test_name.split('.')
        return contract, method, version

    init_problems = [_split_test(test) for test in tests]

    _apr_proofs: list[tuple[bool, list[str] | None]]
    if workers > 1:
        with ProcessPool(ncpus=workers) as process_pool:
            _apr_proofs = process_pool.map(init_and_run_proof, init_problems)
    else:
        _apr_proofs = []
        for init_problem in init_problems:
            _apr_proofs.append(init_and_run_proof(init_problem))

    apr_proofs = dict(zip(tests, _apr_proofs, strict=True))
    return apr_proofs


def method_to_apr_proof(
    foundry: Foundry,
    contract: Contract,
    method: Contract.Method,
    save_directory: Path,
    kcfg_explore: KCFGExplore,
    test_id: str,
    simplify_init: bool = True,
    bmc_depth: int | None = None,
) -> APRProof | APRBMCProof:
    contract_name = contract.name
    method_sig = method.signature
    if Proof.proof_data_exists(test_id, save_directory):
        apr_proof = foundry.get_apr_proof(test_id)
    else:
        _LOGGER.info(f'Initializing KCFG for test: {test_id}')

        setup_digest = None
        if method_sig != 'setUp()' and 'setUp' in contract.method_by_name:
            latest_version = foundry.latest_proof_version(f'{contract.name}.setUp()')
            setup_digest = f'{contract_name}.setUp():{latest_version}'
            _LOGGER.info(f'Using setUp method for test: {test_id}')

        empty_config = foundry.kevm.definition.empty_config(GENERATED_TOP_CELL)
        kcfg, init_node_id, target_node_id = _method_to_cfg(
            empty_config, contract, method, save_directory, init_state=setup_digest
        )

        _LOGGER.info(f'Expanding macros in initial state for test: {test_id}')
        init_term = kcfg.node(init_node_id).cterm.kast
        init_term = KDefinition__expand_macros(foundry.kevm.definition, init_term)
        init_cterm = CTerm.from_kast(init_term)
        _LOGGER.info(f'Computing definedness constraint for test: {test_id}')
        init_cterm = kcfg_explore.cterm_assume_defined(init_cterm)
        kcfg.replace_node(init_node_id, init_cterm)

        _LOGGER.info(f'Expanding macros in target state for test: {test_id}')
        target_term = kcfg.node(target_node_id).cterm.kast
        target_term = KDefinition__expand_macros(foundry.kevm.definition, target_term)
        target_cterm = CTerm.from_kast(target_term)
        kcfg.replace_node(target_node_id, target_cterm)

        if simplify_init:
            _LOGGER.info(f'Simplifying KCFG for test: {test_id}')
            kcfg_explore.simplify(kcfg, {})
        if bmc_depth is not None:
            apr_proof = APRBMCProof(
                test_id,
                kcfg,
                [],
                init_node_id,
                target_node_id,
                {},
                bmc_depth,
                proof_dir=save_directory,
            )
        else:
            apr_proof = APRProof(test_id, kcfg, [], init_node_id, target_node_id, {}, proof_dir=save_directory)

    apr_proof.write_proof_data()
    return apr_proof


def _method_to_cfg(
    empty_config: KInner,
    contract: Contract,
    method: Contract.Method,
    kcfgs_dir: Path,
    init_state: str | None = None,
) -> tuple[KCFG, NodeIdLike, NodeIdLike]:
    calldata = method.calldata_cell(contract)
    callvalue = method.callvalue_cell
    init_cterm = _init_cterm(
        empty_config,
        contract.name,
        kcfgs_dir,
        calldata=calldata,
        callvalue=callvalue,
        init_state=init_state,
    )
    is_test = method.name.startswith('test')
    failing = method.name.startswith('testFail')
    final_cterm = _final_cterm(empty_config, contract.name, failing=failing, is_test=is_test)

    cfg = KCFG()
    init_node = cfg.create_node(init_cterm)
    target_node = cfg.create_node(final_cterm)

    return cfg, init_node.id, target_node.id


def _init_cterm(
    empty_config: KInner,
    contract_name: str,
    kcfgs_dir: Path,
    *,
    calldata: KInner | None = None,
    callvalue: KInner | None = None,
    init_state: str | None = None,
) -> CTerm:
    program = KEVM.bin_runtime(KApply(f'contract_{contract_name}'))
    account_cell = KEVM.account_cell(
        Foundry.address_TEST_CONTRACT(),
        intToken(0),
        program,
        KApply('.Map'),
        KApply('.Map'),
        intToken(1),
    )
    init_subst = {
        'MODE_CELL': KApply('NORMAL'),
        'SCHEDULE_CELL': KApply('SHANGHAI_EVM'),
        'STATUSCODE_CELL': KVariable('STATUSCODE'),
        'CALLSTACK_CELL': KApply('.List'),
        'CALLDEPTH_CELL': intToken(0),
        'PROGRAM_CELL': program,
        'JUMPDESTS_CELL': KEVM.compute_valid_jumpdests(program),
        'ORIGIN_CELL': KVariable('ORIGIN_ID'),
        'LOG_CELL': KApply('.List'),
        'ID_CELL': Foundry.address_TEST_CONTRACT(),
        'CALLER_CELL': KVariable('CALLER_ID'),
        'ACCESSEDACCOUNTS_CELL': KApply('.Set'),
        'ACCESSEDSTORAGE_CELL': KApply('.Map'),
        'INTERIMSTATES_CELL': KApply('.List'),
        'LOCALMEM_CELL': KApply('.Bytes_BYTES-HOOKED_Bytes'),
        'PREVCALLER_CELL': KApply('.Account_EVM-TYPES_Account'),
        'PREVORIGIN_CELL': KApply('.Account_EVM-TYPES_Account'),
        'NEWCALLER_CELL': KApply('.Account_EVM-TYPES_Account'),
        'NEWORIGIN_CELL': KApply('.Account_EVM-TYPES_Account'),
        'ACTIVE_CELL': FALSE,
        'STATIC_CELL': FALSE,
        'MEMORYUSED_CELL': intToken(0),
        'WORDSTACK_CELL': KApply('.WordStack_EVM-TYPES_WordStack'),
        'PC_CELL': intToken(0),
        'GAS_CELL': intToken(9223372036854775807),
        'K_CELL': KSequence([KEVM.sharp_execute(), KVariable('CONTINUATION')]),
        'ACCOUNTS_CELL': KEVM.accounts(
            [
                account_cell,  # test contract address
                Foundry.account_CHEATCODE_ADDRESS(KApply('.Map')),
            ]
        ),
        'SINGLECALL_CELL': FALSE,
        'ISREVERTEXPECTED_CELL': FALSE,
        'ISOPCODEEXPECTED_CELL': FALSE,
        'EXPECTEDADDRESS_CELL': KApply('.Account_EVM-TYPES_Account'),
        'EXPECTEDVALUE_CELL': intToken(0),
        'EXPECTEDDATA_CELL': KApply('.Bytes_BYTES-HOOKED_Bytes'),
        'OPCODETYPE_CELL': KApply('.OpcodeType_FOUNDRY-CHEAT-CODES_OpcodeType'),
        'RECORDEVENT_CELL': FALSE,
        'ISEVENTEXPECTED_CELL': FALSE,
        'ISCALLWHITELISTACTIVE_CELL': FALSE,
        'ISSTORAGEWHITELISTACTIVE_CELL': FALSE,
        'ADDRESSSET_CELL': KApply('.Set'),
        'STORAGESLOTSET_CELL': KApply('.Set'),
    }

    constraints = None
    if init_state:
        accts, constraints = _get_final_accounts_cell(init_state, kcfgs_dir, overwrite_code_cell=program)
        init_subst['ACCOUNTS_CELL'] = accts

    if calldata is not None:
        init_subst['CALLDATA_CELL'] = calldata

    if callvalue is not None:
        init_subst['CALLVALUE_CELL'] = callvalue

    init_term = Subst(init_subst)(empty_config)
    init_cterm = CTerm.from_kast(init_term)
    init_cterm = KEVM.add_invariant(init_cterm)
    if constraints is None:
        return init_cterm
    else:
        for constraint in constraints:
            init_cterm = init_cterm.add_constraint(constraint)
        return init_cterm


def _final_cterm(empty_config: KInner, contract_name: str, *, failing: bool, is_test: bool = True) -> CTerm:
    final_term = _final_term(empty_config, contract_name)
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


def _final_term(empty_config: KInner, contract_name: str) -> KInner:
    program = KEVM.bin_runtime(KApply(f'contract_{contract_name}'))
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
        'ID_CELL': Foundry.address_TEST_CONTRACT(),
        'ACCOUNTS_CELL': KEVM.accounts(
            [
                post_account_cell,  # test contract address
                Foundry.account_CHEATCODE_ADDRESS(KVariable('CHEATCODE_STORAGE_FINAL')),
                KVariable('ACCOUNTS_FINAL'),
            ]
        ),
        'ISREVERTEXPECTED_CELL': KVariable('ISREVERTEXPECTED_FINAL'),
        'ISOPCODEEXPECTED_CELL': KVariable('ISOPCODEEXPECTED_FINAL'),
        'RECORDEVENT_CELL': KVariable('RECORDEVENT_FINAL'),
        'ISEVENTEXPECTED_CELL': KVariable('ISEVENTEXPECTED_FINAL'),
        'ISCALLWHITELISTACTIVE_CELL': KVariable('ISCALLWHITELISTACTIVE_FINAL'),
        'ISSTORAGEWHITELISTACTIVE_CELL': KVariable('ISSTORAGEWHITELISTACTIVE_FINAL'),
        'ADDRESSSET_CELL': KVariable('ADDRESSSET_FINAL'),
        'STORAGESLOTSET_CELL': KVariable('STORAGESLOTSET_FINAL'),
    }
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


def _get_final_accounts_cell(
    proof_id: str, proof_dir: Path, overwrite_code_cell: KInner | None = None
) -> tuple[KInner, Iterable[KInner]]:
    apr_proof = APRProof.read_proof_data(proof_dir, proof_id)
    target = apr_proof.kcfg.node(apr_proof.target)
    target_states = apr_proof.kcfg.covers(target_id=target.id)
    if len(target_states) == 0:
        raise ValueError(
            f'setUp() function for {apr_proof.id} did not reach the end of execution. Maybe --max-iterations is too low?'
        )
    if len(target_states) > 1:
        raise ValueError(f'setUp() function for {apr_proof.id} branched and has {len(target_states)} target states.')
    cterm = single(target_states).source.cterm
    acct_cell = cterm.cell('ACCOUNTS_CELL')

    if overwrite_code_cell is not None:
        new_accounts = [CTerm(account, []) for account in flatten_label('_AccountCellMap_', acct_cell)]
        new_accounts_map = {account.cell('ACCTID_CELL'): account for account in new_accounts}
        test_contract_account = new_accounts_map[Foundry.address_TEST_CONTRACT()]

        new_accounts_map[Foundry.address_TEST_CONTRACT()] = CTerm(
            set_cell(test_contract_account.config, 'CODE_CELL', overwrite_code_cell),
            [],
        )

        acct_cell = KEVM.accounts([account.config for account in new_accounts_map.values()])

    fvars = free_vars(acct_cell)
    acct_cons = constraints_for(fvars, cterm.constraints)
    return (acct_cell, acct_cons)
