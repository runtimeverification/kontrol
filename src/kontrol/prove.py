from __future__ import annotations

import logging
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, NamedTuple

from kevm_pyk.kevm import KEVM, KEVMSemantics
from kevm_pyk.utils import KDefinition__expand_macros, abstract_cell_vars, legacy_explore, run_prover
from pathos.pools import ProcessPool  # type: ignore
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KLabel, KSequence, KSort, KToken, KVariable, Subst
from pyk.kast.manip import flatten_label, set_cell
from pyk.kcfg import KCFG
from pyk.prelude.k import GENERATED_TOP_CELL
from pyk.prelude.kbool import FALSE, TRUE, notBool
from pyk.prelude.kint import eqInt, intToken, leInt
from pyk.prelude.ml import mlEqualsTrue
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRBMCProof, APRProof
from pyk.utils import run_process, unique

from .foundry import Foundry
from .solc_to_k import Contract

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Final

    from pyk.kast.inner import KInner
    from pyk.kcfg import KCFGExplore

    from .options import ProveOptions, RPCOptions


_LOGGER: Final = logging.getLogger(__name__)


def foundry_prove(
    foundry: Foundry,
    prove_options: ProveOptions,
    rpc_options: RPCOptions,
    tests: Iterable[tuple[str, int | None]] = (),
) -> list[Proof]:
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

    def run_prover(test_suite: list[FoundryTest]) -> list[Proof]:
        return _run_cfg_group(
            tests=test_suite,
            foundry=foundry,
            prove_options=prove_options,
            rpc_options=rpc_options,
        )

    if prove_options.run_constructor:
        _LOGGER.info(f'Running initialization code for contracts in parallel: {constructor_names}')
        results = run_prover(constructor_tests)
        failed = [proof for proof in results if not proof.passed]
        if failed:
            raise ValueError(f'Running initialization code failed for {len(failed)} contracts: {failed}')

    _LOGGER.info(f'Running setup functions in parallel: {setup_method_names}')
    results = run_prover(setup_method_tests)

    failed = [proof for proof in results if not proof.passed]
    if failed:
        raise ValueError(f'Running setUp method failed for {len(failed)} contracts: {failed}')

    _LOGGER.info(f'Running test functions in parallel: {test_names}')
    results = run_prover(test_suite)
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


def collect_tests(foundry: Foundry, tests: Iterable[tuple[str, int | None]] = (), *, reinit: bool) -> list[FoundryTest]:
    if not tests:
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
) -> list[Proof]:
    def init_and_run_proof(test: FoundryTest) -> Proof:
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
            )

            run_prover(
                foundry.kevm,
                proof,
                kcfg_explore,
                max_depth=prove_options.max_depth,
                max_iterations=prove_options.max_iterations,
                cut_point_rules=KEVMSemantics.cut_point_rules(
                    prove_options.break_on_jumpi, prove_options.break_on_calls
                ),
                terminal_rules=KEVMSemantics.terminal_rules(prove_options.break_every_step),
                counterexample_info=prove_options.counterexample_info,
            )
            return proof

    apr_proofs: list[Proof]
    if prove_options.workers > 1:
        with ProcessPool(ncpus=prove_options.workers) as process_pool:
            apr_proofs = process_pool.map(init_and_run_proof, tests)
    else:
        apr_proofs = []
        for test in tests:
            apr_proofs.append(init_and_run_proof(test))

    return apr_proofs


def method_to_apr_proof(
    test: FoundryTest,
    foundry: Foundry,
    kcfg_explore: KCFGExplore,
    bmc_depth: int | None = None,
    run_constructor: bool = False,
    use_gas: bool = False,
) -> APRProof | APRBMCProof:
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
        )
    else:
        apr_proof = APRProof(test.id, kcfg, [], init_node_id, target_node_id, {}, proof_dir=foundry.proofs_dir)

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
) -> tuple[KCFG, int, int]:
    _LOGGER.info(f'Initializing KCFG for test: {test.id}')

    empty_config = foundry.kevm.definition.empty_config(GENERATED_TOP_CELL)
    kcfg, new_node_ids, init_node_id, target_node_id = _method_to_cfg(
        empty_config,
        test.contract,
        test.method,
        setup_proof,
        use_gas,
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
) -> tuple[KCFG, list[int], int, int]:
    calldata = None
    callvalue = None

    if isinstance(method, Contract.Constructor):
        program = KEVM.init_bytecode(KApply(f'contract_{contract.name_with_path}'))
        use_init_code = True

    elif isinstance(method, Contract.Method):
        calldata, is_calldata_symbolic = method.calldata_cell(contract)
        callvalue = method.callvalue_cell
        program = KEVM.bin_runtime(KApply(f'contract_{contract.name_with_path}'))
        use_init_code = False

    init_cterm = _init_cterm(
        empty_config,
        contract.name_with_path,
        program=program,
        calldata=calldata,
        is_calldata_symbolic=is_calldata_symbolic,
        callvalue=callvalue,
        use_gas=use_gas,
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
            new_accounts_cell = final_node.cterm.cell('ACCOUNTS_CELL')
            number_cell = final_node.cterm.cell('NUMBER_CELL')
            new_accounts = [CTerm(account, []) for account in flatten_label('_AccountCellMap_', new_accounts_cell)]
            new_accounts_map = {account.cell('ACCTID_CELL'): account for account in new_accounts}
            test_contract_account = new_accounts_map[Foundry.address_TEST_CONTRACT()]

            new_accounts_map[Foundry.address_TEST_CONTRACT()] = CTerm(
                set_cell(
                    test_contract_account.config,
                    'CODE_CELL',
                    KEVM.bin_runtime(KApply(f'contract_{contract.name_with_path}')),
                ),
                [],
            )

            new_accounts_cell = KEVM.accounts([account.config for account in new_accounts_map.values()])

            new_init_cterm = CTerm(set_cell(init_cterm.config, 'ACCOUNTS_CELL', new_accounts_cell), [])
            new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'NUMBER_CELL', number_cell), [])
            # adding constraints from the initial cterm
            for constraint in init_cterm.constraints:
                new_init_cterm = new_init_cterm.add_constraint(constraint)

            new_node = cfg.create_node(new_init_cterm)
            cfg.create_edge(final_node.id, new_node.id, depth=1)
            new_node_ids.append(new_node.id)
    else:
        cfg = KCFG()
        init_node = cfg.create_node(init_cterm)
        new_node_ids = [init_node.id]
        init_node_id = init_node.id

    is_test = method.signature.startswith('test')
    failing = method.signature.startswith('testFail')
    final_cterm = _final_cterm(
        empty_config, contract.name_with_path, failing=failing, is_test=is_test, use_init_code=use_init_code
    )
    target_node = cfg.create_node(final_cterm)

    return cfg, new_node_ids, init_node_id, target_node.id


def _init_cterm(
    empty_config: KInner,
    contract_name: str,
    program: KInner,
    use_gas: bool,
    *,
    setup_cterm: CTerm | None = None,
    calldata: KInner | None = None,
    is_calldata_symbolic: bool = False,
    callvalue: KInner | None = None,
) -> CTerm:
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
        'USEGAS_CELL': TRUE if use_gas else FALSE,
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
        'GAS_CELL': KEVM.inf_gas(KVariable('VGAS')),
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

    if calldata is not None:
        init_subst['CALLDATA_CELL'] = calldata
        constraints = []

        if is_calldata_symbolic:
            # TODO(palina): EXPERIMENTAL: if calldata is symbolic,
            # add assumptions that correspond to the test w/`BYTES_DATA` being 320 bytes long, and `bytes[]` containing
            # 10 elements, each 600 bytes long
            # structured_calldata_constraints = structured_calldata_assumptions()
            # constraints.extend(structured_calldata_constraints)

            # TODO(palina):
            # add assumptions that correspond to the test w/`BYTES_DATA` having symbolic length, and `bytes[]` containing
            # 10 elements, each 600 bytes long
            structured_calldata_symbolic_data_constraints = structured_calldata_symbolic_data_assumptions()
            constraints.extend(structured_calldata_symbolic_data_constraints)

            # TODO(palina): uncomment to add assumptions that correspond to compiler-inserted checks on fully symbolic calldata
            # compiler_constraints = compiler_assumptions(calldata)
            # constraints.extend(compiler_constraints)

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


def structured_calldata_assumptions() -> list[KApply]:
    constraints = []

    target_constraint = mlEqualsTrue(KEVM.range_address(KVariable('target', 'Int')))
    sender_constraint = mlEqualsTrue(KEVM.range_address(KVariable('sender', 'Int')))
    l2_output_constraint = mlEqualsTrue(KEVM.range_uint('256', KVariable('l2OutputIndex', 'Int')))
    constraints.append(l2_output_constraint)

    constraints.append(target_constraint)
    constraints.append(sender_constraint)

    length_bytes_data_constraint = mlEqualsTrue(
        eqInt(KEVM.size_bytes(KVariable('BYTES_DATA', 'Bytes')), intToken("320"))
    )
    constraints.append(length_bytes_data_constraint)

    length_bytes_arr_constraint_1 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_1', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_1)
    length_bytes_arr_constraint_2 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_2', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_2)
    length_bytes_arr_constraint_3 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_3', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_3)
    length_bytes_arr_constraint_4 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_4', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_4)
    length_bytes_arr_constraint_5 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_5', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_5)
    length_bytes_arr_constraint_6 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_6', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_6)
    length_bytes_arr_constraint_7 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_7', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_7)
    length_bytes_arr_constraint_8 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_8', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_8)
    length_bytes_arr_constraint_9 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_9', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_9)
    length_bytes_arr_constraint_10 = mlEqualsTrue(
        eqInt(KEVM.size_bytes(KVariable('BYTES_10', 'Bytes')), intToken("600"))
    )
    constraints.append(length_bytes_arr_constraint_10)
    return constraints


def structured_calldata_symbolic_data_assumptions() -> list[KApply]:
    constraints = []

    target_constraint = mlEqualsTrue(KEVM.range_address(KVariable('target', 'Int')))
    sender_constraint = mlEqualsTrue(KEVM.range_address(KVariable('sender', 'Int')))
    l2_output_constraint = mlEqualsTrue(KEVM.range_uint('256', KVariable('l2OutputIndex', 'Int')))
    constraints.append(l2_output_constraint)

    constraints.append(target_constraint)
    constraints.append(sender_constraint)

    length_bytes_data_equality = mlEqualsTrue(
        eqInt(KEVM.size_bytes(KVariable('BYTES_DATA', 'Bytes')), KVariable('BYTES_SIZE', 'Int'))
    )

    # Size of the symbolic bytes is limited to 1Mb
    length_bytes_data_constraint = mlEqualsTrue(leInt(KVariable('BYTES_SIZE', 'Int'), intToken("1073741824")))

    constraints.append(length_bytes_data_equality)
    constraints.append(length_bytes_data_constraint)

    length_bytes_arr_constraint_1 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_1', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_1)
    length_bytes_arr_constraint_2 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_2', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_2)
    length_bytes_arr_constraint_3 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_3', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_3)
    length_bytes_arr_constraint_4 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_4', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_4)
    length_bytes_arr_constraint_5 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_5', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_5)
    length_bytes_arr_constraint_6 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_6', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_6)
    length_bytes_arr_constraint_7 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_7', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_7)
    length_bytes_arr_constraint_8 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_8', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_8)
    length_bytes_arr_constraint_9 = mlEqualsTrue(eqInt(KEVM.size_bytes(KVariable('BYTES_9', 'Bytes')), intToken("600")))
    constraints.append(length_bytes_arr_constraint_9)
    length_bytes_arr_constraint_10 = mlEqualsTrue(
        eqInt(KEVM.size_bytes(KVariable('BYTES_10', 'Bytes')), intToken("600"))
    )
    constraints.append(length_bytes_arr_constraint_10)
    return constraints


def compiler_assumptions(calldata: KInner) -> list[KApply]:
    constraints = []
    chopped_calldata_length = KApply('chop(_)_WORD_Int_Int', [KEVM.size_bytes(KVariable('SYMBOLIC_CALLDATA'))])
    # calldata_length_range = mlEqualsTrue(leInt(KEVM.size_bytes(KVariable('SYMBOLIC_CALLDATA')), KEVM.pow256()))
    # constraints.append(calldata_length_range)
    calldata_length_416 = mlEqualsTrue(
        eqInt(intToken(0), KApply('_s<Word__EVM-TYPES_Int_Int_Int', [chopped_calldata_length, intToken(416)]))
    )
    constraints.append(calldata_length_416)

    # asWord(#range(SYMBOLIC_CALLDATA, 0, 32)) <=Int maxUInt64
    offset_struct = KApply(
        '#asWord(_)_EVM-TYPES_Int_Bytes',
        [
            KApply(
                '#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                [KVariable('SYMBOLIC_CALLDATA'), intToken(0), intToken(32)],
            )
        ],
    )
    constraints.append(mlEqualsTrue(leInt(offset_struct, intToken("18446744073709551615"))))

    # asWord(#range(SYMBOLIC_CALLDATA, 0, 32)) == 224
    first_offset = eqInt(offset_struct, intToken(224))
    constraints.append(mlEqualsTrue(first_offset))

    # And { true #Equals ( (chop ( ( ( lengthBytes ( SYMBOLIC_CALLDATA:Bytes ) -Int chop ( ( #asWord ( #range ( SYMBOLIC_CALLDATA:Bytes , 0 , 32 ) ) +Int 4 ) ) ) +Int 4 ) )) s<Word (192) ) ==Int 0 } ) ) ) ) ) ) ) ) ) ) )
    # And { true #Equals ( (chop ( ( ( lengthBytes ( SYMBOLIC_CALLDATA:Bytes ) -Int chop ( ( #asWord ( #range ( SYMBOLIC_CALLDATA:Bytes , 0 , 32 ) ) +Int 4 ) ) ) +Int 4 ) )) s<Word (192) ) ==Int 0 } ) ) ) ) ) ) ) ) ) ) )
    struct_loc = KApply('chop(_)_WORD_Int_Int', [KApply('_+Int_', [offset_struct, intToken(4)])])
    struct_subtr = KApply(
        'chop(_)_WORD_Int_Int',
        [
            KApply(
                '_+Int_',
                [KApply('_-Int_', [KEVM.size_bytes(KVariable('SYMBOLIC_CALLDATA')), struct_loc]), intToken(4)],
            )
        ],
    )
    struct_length_192 = mlEqualsTrue(
        eqInt(intToken(0), KApply('_s<Word__EVM-TYPES_Int_Int_Int', [struct_subtr, intToken(192)]))
    )
    constraints.append(struct_length_192)

    # asWord ( #range ( b"\xfd'\xd8\xba" +Bytes SYMBOLIC_CALLDATA:Bytes , chop ( ( chop ( ( #asWord ( #range ( SYMBOLIC_CALLDATA:Bytes , 0 , 32 ) ) +Int 4 ) ) +Int 32 ) ) , 32 ) )
    # Equals ( maxUInt160 &Int #asWord ( #range ( b"\xfd'\xd8\xba" +Bytes SYMBOLIC_CALLDATA:Bytes , chop ( ( chop ( ( #asWord ( #range ( SYMBOLIC_CALLDATA:Bytes , 0 , 32 ) ) +Int 4 ) ) +Int 32 ) ) , 32 ) ) )
    struct_data_one = KApply('chop(_)_WORD_Int_Int', [KApply('_+Int_', [struct_loc, intToken(32)])])
    struct_data_one_lhs = KApply(
        '#asWord(_)_EVM-TYPES_Int_Bytes',
        [KApply('#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int', [calldata, struct_data_one, intToken(32)])],
    )
    struct_data_one_rhs = KApply(
        '_&Int_', [intToken(1461501637330902918203684832716283019655932542975), struct_data_one_lhs]
    )
    struct_data_one_constraint = mlEqualsTrue(eqInt(struct_data_one_lhs, struct_data_one_rhs))
    constraints.append(struct_data_one_constraint)

    # asWord ( #range ( b"\xfd'\xd8\xba" +Bytes SYMBOLIC_CALLDATA:Bytes , chop ( ( chop ( ( #asWord ( #range ( SYMBOLIC_CALLDATA:Bytes , 0 , 32 ) ) +Int 4 ) ) +Int 32 ) ) , 32 ) )
    # Equals ( maxUInt160 &Int #asWord ( #range ( b"\xfd'\xd8\xba" +Bytes SYMBOLIC_CALLDATA:Bytes , chop ( ( chop ( ( #asWord ( #range ( SYMBOLIC_CALLDATA:Bytes , 0 , 32 ) ) +Int 4 ) ) +Int 32 ) ) , 32 ) ) )
    struct_data_two = KApply('chop(_)_WORD_Int_Int', [KApply('_+Int_', [struct_loc, intToken(64)])])
    struct_data_two_lhs = KApply(
        '#asWord(_)_EVM-TYPES_Int_Bytes',
        [KApply('#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int', [calldata, struct_data_two, intToken(32)])],
    )
    struct_data_two_rhs = KApply(
        '_&Int_', [intToken(1461501637330902918203684832716283019655932542975), struct_data_two_lhs]
    )
    struct_data_two_constraint = mlEqualsTrue(eqInt(struct_data_two_lhs, struct_data_two_rhs))
    constraints.append(struct_data_two_constraint)

    # ( (chop ( ( chop ( ( chop ( ( #asWord ( #range ( SYMBOLIC_CALLDATA:Bytes , 0 , 32 ) ) +Int 4 ) )
    #    +Int #asWord ( #range ( b"\xfd'\xd8\xba" +Bytes SYMBOLIC_CALLDATA:Bytes , chop ( ( chop ( ( #asWord ( #range ( SYMBOLIC_CALLDATA:Bytes , 0 , 32 ) ) +Int 4 ) ) +Int 160 ) ) , 32 ) ) ) ) +Int maxUInt5 ) ))
    #  s<Word (( lengthBytes ( SYMBOLIC_CALLDATA:Bytes ) +Int 4 )) ) ==Int 0
    struct_three = KApply('chop(_)_WORD_Int_Int', [KApply('_+Int_', [struct_loc, intToken(160)])])
    struct_array_offset = KApply(
        '#asWord(_)_EVM-TYPES_Int_Bytes',
        [KApply('#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int', [calldata, struct_three, intToken(32)])],
    )
    struct_three_lhs_lhs_two = KApply('chop(_)_WORD_Int_Int', [KApply('_+Int_', [struct_loc, struct_array_offset])])
    struct_three_lhs_sum = KApply('chop(_)_WORD_Int_Int', [KApply('_+Int_', [struct_three_lhs_lhs_two, intToken(31)])])
    struct_three_rhs = KApply('_+Int_', [KEVM.size_bytes(KVariable('SYMBOLIC_CALLDATA')), intToken(4)])
    struct_three_constraint = mlEqualsTrue(
        notBool(eqInt(intToken(0), KApply('_s<Word__EVM-TYPES_Int_Int_Int', [struct_three_lhs_sum, struct_three_rhs])))
    )
    constraints.append(struct_three_constraint)

    struct_array_offset_constraint = mlEqualsTrue(leInt(struct_array_offset, intToken("18446744073709551615")))
    constraints.append(struct_array_offset_constraint)

    array_length_lhs_one = KApply(
        '#asWord(_)_EVM-TYPES_Int_Bytes',
        [
            KApply(
                '#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                [
                    calldata,
                    KApply(
                        'chop(_)_WORD_Int_Int',
                        [
                            KApply(
                                '_+Int_',
                                [
                                    KApply(
                                        '_+Int_',
                                        [
                                            offset_struct,
                                            KApply(
                                                '#asWord(_)_EVM-TYPES_Int_Bytes',
                                                [
                                                    KApply(
                                                        '#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                        [
                                                            calldata,
                                                            KApply('_+Int_', [offset_struct, intToken(164)]),
                                                            intToken(32),
                                                        ],
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                    intToken(4),
                                ],
                            )
                        ],
                    ),
                    intToken(32),
                ],
            )
        ],
    )
    constraints.append(mlEqualsTrue(leInt(array_length_lhs_one, intToken("18446744073709551615"))))

    chopped_val = KApply(
        label=KLabel(name='chop(_)_WORD_Int_Int', params=()),
        args=(
            KApply(
                label=KLabel(name='_+Int_', params=()),
                args=(
                    KApply(
                        label=KLabel(name='_&Int_', params=()),
                        args=(
                            KToken(
                                token='115792089237316195423570985008687907853269984665640564039457584007913129639904',
                                sort=KSort(name='Int'),
                            ),
                            KApply(
                                label=KLabel(name='chop(_)_WORD_Int_Int', params=()),
                                args=(
                                    KApply(
                                        label=KLabel(name='_+Int_', params=()),
                                        args=(
                                            KApply(
                                                label=KLabel(name='_&Int_', params=()),
                                                args=(
                                                    KToken(
                                                        token='115792089237316195423570985008687907853269984665640564039457584007913129639904',
                                                        sort=KSort(name='Int'),
                                                    ),
                                                    KApply(
                                                        label=KLabel(name='_+Int_', params=()),
                                                        args=(
                                                            KApply(
                                                                label=KLabel(
                                                                    name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                    params=(),
                                                                ),
                                                                args=(
                                                                    KApply(
                                                                        label=KLabel(
                                                                            name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                            params=(),
                                                                        ),
                                                                        args=(
                                                                            KApply(
                                                                                label=KLabel(
                                                                                    name='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                                                                                    params=(),
                                                                                ),
                                                                                args=(
                                                                                    KToken(
                                                                                        token='b"\\xfd\'\\xd8\\xba"',
                                                                                        sort=KSort(name='Bytes'),
                                                                                    ),
                                                                                    KVariable(
                                                                                        name='SYMBOLIC_CALLDATA',
                                                                                        sort=KSort(name='Bytes'),
                                                                                    ),
                                                                                ),
                                                                            ),
                                                                            KApply(
                                                                                label=KLabel(
                                                                                    name='chop(_)_WORD_Int_Int',
                                                                                    params=(),
                                                                                ),
                                                                                args=(
                                                                                    KApply(
                                                                                        label=KLabel(
                                                                                            name='_+Int_',
                                                                                            params=(),
                                                                                        ),
                                                                                        args=(
                                                                                            KApply(
                                                                                                label=KLabel(
                                                                                                    name='_+Int_',
                                                                                                    params=(),
                                                                                                ),
                                                                                                args=(
                                                                                                    KApply(
                                                                                                        label=KLabel(
                                                                                                            name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                                                            params=(),
                                                                                                        ),
                                                                                                        args=(
                                                                                                            KApply(
                                                                                                                label=KLabel(
                                                                                                                    name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                                                                    params=(),
                                                                                                                ),
                                                                                                                args=(
                                                                                                                    KVariable(
                                                                                                                        name='SYMBOLIC_CALLDATA',
                                                                                                                        sort=KSort(
                                                                                                                            name='Bytes'
                                                                                                                        ),
                                                                                                                    ),
                                                                                                                    KToken(
                                                                                                                        token='0',
                                                                                                                        sort=KSort(
                                                                                                                            name='Int'
                                                                                                                        ),
                                                                                                                    ),
                                                                                                                    KToken(
                                                                                                                        token='32',
                                                                                                                        sort=KSort(
                                                                                                                            name='Int'
                                                                                                                        ),
                                                                                                                    ),
                                                                                                                ),
                                                                                                            ),
                                                                                                        ),
                                                                                                    ),
                                                                                                    KApply(
                                                                                                        label=KLabel(
                                                                                                            name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                                                            params=(),
                                                                                                        ),
                                                                                                        args=(
                                                                                                            KApply(
                                                                                                                label=KLabel(
                                                                                                                    name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                                                                    params=(),
                                                                                                                ),
                                                                                                                args=(
                                                                                                                    KApply(
                                                                                                                        label=KLabel(
                                                                                                                            name='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                                                                                                                            params=(),
                                                                                                                        ),
                                                                                                                        args=(
                                                                                                                            KToken(
                                                                                                                                token='b"\\xfd\'\\xd8\\xba"',
                                                                                                                                sort=KSort(
                                                                                                                                    name='Bytes'
                                                                                                                                ),
                                                                                                                            ),
                                                                                                                            KVariable(
                                                                                                                                name='SYMBOLIC_CALLDATA',
                                                                                                                                sort=KSort(
                                                                                                                                    name='Bytes'
                                                                                                                                ),
                                                                                                                            ),
                                                                                                                        ),
                                                                                                                    ),
                                                                                                                    KApply(
                                                                                                                        label=KLabel(
                                                                                                                            name='_+Int_',
                                                                                                                            params=(),
                                                                                                                        ),
                                                                                                                        args=(
                                                                                                                            KApply(
                                                                                                                                label=KLabel(
                                                                                                                                    name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                                                                                    params=(),
                                                                                                                                ),
                                                                                                                                args=(
                                                                                                                                    KApply(
                                                                                                                                        label=KLabel(
                                                                                                                                            name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                                                                                            params=(),
                                                                                                                                        ),
                                                                                                                                        args=(
                                                                                                                                            KVariable(
                                                                                                                                                name='SYMBOLIC_CALLDATA',
                                                                                                                                                sort=KSort(
                                                                                                                                                    name='Bytes'
                                                                                                                                                ),
                                                                                                                                            ),
                                                                                                                                            KToken(
                                                                                                                                                token='0',
                                                                                                                                                sort=KSort(
                                                                                                                                                    name='Int'
                                                                                                                                                ),
                                                                                                                                            ),
                                                                                                                                            KToken(
                                                                                                                                                token='32',
                                                                                                                                                sort=KSort(
                                                                                                                                                    name='Int'
                                                                                                                                                ),
                                                                                                                                            ),
                                                                                                                                        ),
                                                                                                                                    ),
                                                                                                                                ),
                                                                                                                            ),
                                                                                                                            KToken(
                                                                                                                                token='164',
                                                                                                                                sort=KSort(
                                                                                                                                    name='Int'
                                                                                                                                ),
                                                                                                                            ),
                                                                                                                        ),
                                                                                                                    ),
                                                                                                                    KToken(
                                                                                                                        token='32',
                                                                                                                        sort=KSort(
                                                                                                                            name='Int'
                                                                                                                        ),
                                                                                                                    ),
                                                                                                                ),
                                                                                                            ),
                                                                                                        ),
                                                                                                    ),
                                                                                                ),
                                                                                            ),
                                                                                            KToken(
                                                                                                token='4',
                                                                                                sort=KSort(name='Int'),
                                                                                            ),
                                                                                        ),
                                                                                    ),
                                                                                ),
                                                                            ),
                                                                            KToken(
                                                                                token='32',
                                                                                sort=KSort(name='Int'),
                                                                            ),
                                                                        ),
                                                                    ),
                                                                ),
                                                            ),
                                                            KToken(
                                                                token='31',
                                                                sort=KSort(name='Int'),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            KToken(token='63', sort=KSort(name='Int')),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    KToken(token='320', sort=KSort(name='Int')),
                ),
            ),
        ),
    )
    notMaxUint5_term = KApply(
        label=KLabel(name='notBool_', params=()),
        args=(
            KApply(
                label=KLabel(name='_orBool_', params=()),
                args=(
                    KApply(
                        label=KLabel(name='_<Int_', params=()),
                        args=(
                            chopped_val,
                            KToken(token='320', sort=KSort(name='Int')),
                        ),
                    ),
                    KApply(
                        label=KLabel(name='_<Int_', params=()),
                        args=(KToken(token='18446744073709551615', sort=KSort(name='Int')), chopped_val),
                    ),
                ),
            ),
        ),
    )

    constraints.append(mlEqualsTrue(notMaxUint5_term))

    another_term = KApply(
        label=KLabel(name='_<=Int_', params=()),
        args=(
            KApply(
                label=KLabel(name='_+Int_', params=()),
                args=(
                    KApply(
                        label=KLabel(name='chop(_)_WORD_Int_Int', params=()),
                        args=(
                            KApply(
                                label=KLabel(name='_+Int_', params=()),
                                args=(
                                    KApply(
                                        label=KLabel(name='_+Int_', params=()),
                                        args=(
                                            KApply(
                                                label=KLabel(name='_+Int_', params=()),
                                                args=(
                                                    KApply(
                                                        label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                                                        args=(
                                                            KApply(
                                                                label=KLabel(
                                                                    name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                    params=(),
                                                                ),
                                                                args=(
                                                                    KVariable(
                                                                        name='SYMBOLIC_CALLDATA',
                                                                        sort=KSort(name='Bytes'),
                                                                    ),
                                                                    KToken(token='0', sort=KSort(name='Int')),
                                                                    KToken(token='32', sort=KSort(name='Int')),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                    KApply(
                                                        label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                                                        args=(
                                                            KApply(
                                                                label=KLabel(
                                                                    name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                    params=(),
                                                                ),
                                                                args=(
                                                                    KApply(
                                                                        label=KLabel(
                                                                            name='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                                                                            params=(),
                                                                        ),
                                                                        args=(
                                                                            KToken(
                                                                                token='b"\\xfd\'\\xd8\\xba"',
                                                                                sort=KSort(name='Bytes'),
                                                                            ),
                                                                            KVariable(
                                                                                name='SYMBOLIC_CALLDATA',
                                                                                sort=KSort(name='Bytes'),
                                                                            ),
                                                                        ),
                                                                    ),
                                                                    KApply(
                                                                        label=KLabel(name='_+Int_', params=()),
                                                                        args=(
                                                                            KApply(
                                                                                label=KLabel(
                                                                                    name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                                    params=(),
                                                                                ),
                                                                                args=(
                                                                                    KApply(
                                                                                        label=KLabel(
                                                                                            name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                                            params=(),
                                                                                        ),
                                                                                        args=(
                                                                                            KVariable(
                                                                                                name='SYMBOLIC_CALLDATA',
                                                                                                sort=KSort(
                                                                                                    name='Bytes'
                                                                                                ),
                                                                                            ),
                                                                                            KToken(
                                                                                                token='0',
                                                                                                sort=KSort(name='Int'),
                                                                                            ),
                                                                                            KToken(
                                                                                                token='32',
                                                                                                sort=KSort(name='Int'),
                                                                                            ),
                                                                                        ),
                                                                                    ),
                                                                                ),
                                                                            ),
                                                                            KToken(
                                                                                token='164',
                                                                                sort=KSort(name='Int'),
                                                                            ),
                                                                        ),
                                                                    ),
                                                                    KToken(token='32', sort=KSort(name='Int')),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            KApply(
                                                label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                                                args=(
                                                    KApply(
                                                        label=KLabel(
                                                            name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                            params=(),
                                                        ),
                                                        args=(
                                                            KApply(
                                                                label=KLabel(
                                                                    name='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                                                                    params=(),
                                                                ),
                                                                args=(
                                                                    KToken(
                                                                        token='b"\\xfd\'\\xd8\\xba"',
                                                                        sort=KSort(name='Bytes'),
                                                                    ),
                                                                    KVariable(
                                                                        name='SYMBOLIC_CALLDATA',
                                                                        sort=KSort(name='Bytes'),
                                                                    ),
                                                                ),
                                                            ),
                                                            KApply(
                                                                label=KLabel(name='chop(_)_WORD_Int_Int', params=()),
                                                                args=(
                                                                    KApply(
                                                                        label=KLabel(name='_+Int_', params=()),
                                                                        args=(
                                                                            KApply(
                                                                                label=KLabel(name='_+Int_', params=()),
                                                                                args=(
                                                                                    KApply(
                                                                                        label=KLabel(
                                                                                            name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                                            params=(),
                                                                                        ),
                                                                                        args=(
                                                                                            KApply(
                                                                                                label=KLabel(
                                                                                                    name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                                                    params=(),
                                                                                                ),
                                                                                                args=(
                                                                                                    KVariable(
                                                                                                        name='SYMBOLIC_CALLDATA',
                                                                                                        sort=KSort(
                                                                                                            name='Bytes'
                                                                                                        ),
                                                                                                    ),
                                                                                                    KToken(
                                                                                                        token='0',
                                                                                                        sort=KSort(
                                                                                                            name='Int'
                                                                                                        ),
                                                                                                    ),
                                                                                                    KToken(
                                                                                                        token='32',
                                                                                                        sort=KSort(
                                                                                                            name='Int'
                                                                                                        ),
                                                                                                    ),
                                                                                                ),
                                                                                            ),
                                                                                        ),
                                                                                    ),
                                                                                    KApply(
                                                                                        label=KLabel(
                                                                                            name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                                            params=(),
                                                                                        ),
                                                                                        args=(
                                                                                            KApply(
                                                                                                label=KLabel(
                                                                                                    name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                                                    params=(),
                                                                                                ),
                                                                                                args=(
                                                                                                    KApply(
                                                                                                        label=KLabel(
                                                                                                            name='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                                                                                                            params=(),
                                                                                                        ),
                                                                                                        args=(
                                                                                                            KToken(
                                                                                                                token='b"\\xfd\'\\xd8\\xba"',
                                                                                                                sort=KSort(
                                                                                                                    name='Bytes'
                                                                                                                ),
                                                                                                            ),
                                                                                                            KVariable(
                                                                                                                name='SYMBOLIC_CALLDATA',
                                                                                                                sort=KSort(
                                                                                                                    name='Bytes'
                                                                                                                ),
                                                                                                            ),
                                                                                                        ),
                                                                                                    ),
                                                                                                    KApply(
                                                                                                        label=KLabel(
                                                                                                            name='_+Int_',
                                                                                                            params=(),
                                                                                                        ),
                                                                                                        args=(
                                                                                                            KApply(
                                                                                                                label=KLabel(
                                                                                                                    name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                                                                    params=(),
                                                                                                                ),
                                                                                                                args=(
                                                                                                                    KApply(
                                                                                                                        label=KLabel(
                                                                                                                            name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                                                                            params=(),
                                                                                                                        ),
                                                                                                                        args=(
                                                                                                                            KVariable(
                                                                                                                                name='SYMBOLIC_CALLDATA',
                                                                                                                                sort=KSort(
                                                                                                                                    name='Bytes'
                                                                                                                                ),
                                                                                                                            ),
                                                                                                                            KToken(
                                                                                                                                token='0',
                                                                                                                                sort=KSort(
                                                                                                                                    name='Int'
                                                                                                                                ),
                                                                                                                            ),
                                                                                                                            KToken(
                                                                                                                                token='32',
                                                                                                                                sort=KSort(
                                                                                                                                    name='Int'
                                                                                                                                ),
                                                                                                                            ),
                                                                                                                        ),
                                                                                                                    ),
                                                                                                                ),
                                                                                                            ),
                                                                                                            KToken(
                                                                                                                token='164',
                                                                                                                sort=KSort(
                                                                                                                    name='Int'
                                                                                                                ),
                                                                                                            ),
                                                                                                        ),
                                                                                                    ),
                                                                                                    KToken(
                                                                                                        token='32',
                                                                                                        sort=KSort(
                                                                                                            name='Int'
                                                                                                        ),
                                                                                                    ),
                                                                                                ),
                                                                                            ),
                                                                                        ),
                                                                                    ),
                                                                                ),
                                                                            ),
                                                                            KToken(
                                                                                token='4',
                                                                                sort=KSort(name='Int'),
                                                                            ),
                                                                        ),
                                                                    ),
                                                                ),
                                                            ),
                                                            KToken(token='32', sort=KSort(name='Int')),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                    KToken(token='36', sort=KSort(name='Int')),
                                ),
                            ),
                        ),
                    ),
                    KToken(token='-4', sort=KSort(name='Int')),
                ),
            ),
            KApply(
                label=KLabel(name='lengthBytes(_)_BYTES-HOOKED_Int_Bytes', params=()),
                args=(KVariable(name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')),),
            ),
        ),
    )
    constraints.append(mlEqualsTrue(another_term))

    new_term = KApply(
        label=KLabel(name='_==Int_', params=()),
        args=(
            KApply(
                label=KLabel(name='_s<Word__EVM-TYPES_Int_Int_Int', params=()),
                args=(
                    KApply(
                        label=KLabel(name='chop(_)_WORD_Int_Int', params=()),
                        args=(
                            KApply(
                                label=KLabel(name='_+Int_', params=()),
                                args=(
                                    KApply(
                                        label=KLabel(name='lengthBytes(_)_BYTES-HOOKED_Int_Bytes', params=()),
                                        args=(KVariable(name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')),),
                                    ),
                                    KToken(token='-64', sort=KSort(name='Int')),
                                ),
                            ),
                        ),
                    ),
                    KToken(token='128', sort=KSort(name='Int')),
                ),
            ),
            KToken(token='0', sort=KSort(name='Int')),
        ),
    )
    constraints.append(mlEqualsTrue(new_term))

    another_offset_check = KApply(
        label=KLabel(name='_<=Int_', params=()),
        args=(
            KApply(
                label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                args=(
                    KApply(
                        label=KLabel(name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int', params=()),
                        args=(
                            KVariable(name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')),
                            KToken(token='192', sort=KSort(name='Int')),
                            KToken(token='32', sort=KSort(name='Int')),
                        ),
                    ),
                ),
            ),
            KToken(token='18446744073709551615', sort=KSort(name='Int')),
        ),
    )
    constraints.append(mlEqualsTrue(another_offset_check))

    bytes_one = notBool(
        KApply(
            label=KLabel(name='_==Int_', params=()),
            args=(
                KApply(
                    label=KLabel(name='_s<Word__EVM-TYPES_Int_Int_Int', params=()),
                    args=(
                        KApply(
                            label=KLabel(name='_+Int_', params=()),
                            args=(
                                KApply(
                                    label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                                    args=(
                                        KApply(
                                            label=KLabel(name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int', params=()),
                                            args=(
                                                KVariable(name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')),
                                                KToken(token='192', sort=KSort(name='Int')),
                                                KToken(token='32', sort=KSort(name='Int')),
                                            ),
                                        ),
                                    ),
                                ),
                                KToken(token='35', sort=KSort(name='Int')),
                            ),
                        ),
                        KApply(
                            label=KLabel(name='_+Int_', params=()),
                            args=(
                                KApply(
                                    label=KLabel(name='lengthBytes(_)_BYTES-HOOKED_Int_Bytes', params=()),
                                    args=(KVariable(name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')),),
                                ),
                                KToken(token='4', sort=KSort(name='Int')),
                            ),
                        ),
                    ),
                ),
                KToken(token='0', sort=KSort(name='Int')),
            ),
        )
    )
    constraints.append(mlEqualsTrue(bytes_one))

    bytes_two = KApply(
        label=KLabel(name='_<=Int_', params=()),
        args=(
            KApply(
                label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                args=(
                    KApply(
                        label=KLabel(name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int', params=()),
                        args=(
                            KVariable(name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')),
                            KApply(
                                label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                                args=(
                                    KApply(
                                        label=KLabel(name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int', params=()),
                                        args=(
                                            KVariable(name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')),
                                            KToken(token='192', sort=KSort(name='Int')),
                                            KToken(token='32', sort=KSort(name='Int')),
                                        ),
                                    ),
                                ),
                            ),
                            KToken(token='32', sort=KSort(name='Int')),
                        ),
                    ),
                ),
            ),
            KToken(token='18446744073709551615', sort=KSort(name='Int')),
        ),
    )
    constraints.append(mlEqualsTrue(bytes_two))

    bytes_three = KApply(
        label=KLabel(name='_<=Int_', params=()),
        args=(
            KApply(
                label=KLabel(name='_+Int_', params=()),
                args=(
                    KApply(
                        label=KLabel(name='chop(_)_WORD_Int_Int', params=()),
                        args=(
                            KApply(
                                label=KLabel(name='_+Int_', params=()),
                                args=(
                                    KApply(
                                        label=KLabel(name='_+Int_', params=()),
                                        args=(
                                            KApply(
                                                label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                                                args=(
                                                    KApply(
                                                        label=KLabel(
                                                            name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                            params=(),
                                                        ),
                                                        args=(
                                                            KVariable(
                                                                name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')
                                                            ),
                                                            KToken(token='192', sort=KSort(name='Int')),
                                                            KToken(token='32', sort=KSort(name='Int')),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            KApply(
                                                label=KLabel(name='_<<Int_', params=()),
                                                args=(
                                                    KApply(
                                                        label=KLabel(name='#asWord(_)_EVM-TYPES_Int_Bytes', params=()),
                                                        args=(
                                                            KApply(
                                                                label=KLabel(
                                                                    name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                    params=(),
                                                                ),
                                                                args=(
                                                                    KVariable(
                                                                        name='SYMBOLIC_CALLDATA',
                                                                        sort=KSort(name='Bytes'),
                                                                    ),
                                                                    KApply(
                                                                        label=KLabel(
                                                                            name='#asWord(_)_EVM-TYPES_Int_Bytes',
                                                                            params=(),
                                                                        ),
                                                                        args=(
                                                                            KApply(
                                                                                label=KLabel(
                                                                                    name='#range(_,_,_)_EVM-TYPES_Bytes_Bytes_Int_Int',
                                                                                    params=(),
                                                                                ),
                                                                                args=(
                                                                                    KVariable(
                                                                                        name='SYMBOLIC_CALLDATA',
                                                                                        sort=KSort(name='Bytes'),
                                                                                    ),
                                                                                    KToken(
                                                                                        token='192',
                                                                                        sort=KSort(name='Int'),
                                                                                    ),
                                                                                    KToken(
                                                                                        token='32',
                                                                                        sort=KSort(name='Int'),
                                                                                    ),
                                                                                ),
                                                                            ),
                                                                        ),
                                                                    ),
                                                                    KToken(token='32', sort=KSort(name='Int')),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                    KToken(token='5', sort=KSort(name='Int')),
                                                ),
                                            ),
                                        ),
                                    ),
                                    KToken(token='36', sort=KSort(name='Int')),
                                ),
                            ),
                        ),
                    ),
                    KToken(token='-4', sort=KSort(name='Int')),
                ),
            ),
            KApply(
                label=KLabel(name='lengthBytes(_)_BYTES-HOOKED_Int_Bytes', params=()),
                args=(KVariable(name='SYMBOLIC_CALLDATA', sort=KSort(name='Bytes')),),
            ),
        ),
    )
    constraints.append(mlEqualsTrue(bytes_three))
    return constraints


def _final_cterm(
    empty_config: KInner, contract_name: str, *, failing: bool, is_test: bool = True, use_init_code: bool = False
) -> CTerm:
    final_term = _final_term(empty_config, contract_name, use_init_code=use_init_code)
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


def _final_term(empty_config: KInner, contract_name: str, use_init_code: bool = False) -> KInner:
    program = (
        KEVM.init_bytecode(KApply(f'contract_{contract_name}'))
        if use_init_code
        else KEVM.bin_runtime(KApply(f'contract_{contract_name}'))
    )
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
