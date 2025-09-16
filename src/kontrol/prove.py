from __future__ import annotations

import logging
import sys
import time
from abc import abstractmethod
from collections import Counter
from copy import copy
from functools import partial
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any, ContextManager, NamedTuple

from kevm_pyk.cli import EVMChainOptions
from kevm_pyk.kevm import KEVM, _process_jumpdests
from kevm_pyk.utils import KDefinition__expand_macros, abstract_cell_vars, run_prover
from multiprocess.pool import Pool  # type: ignore
from pyk.cterm import CTerm, CTermSymbolic
from pyk.kast.inner import KApply, KSequence, KSort, KVariable, Subst
from pyk.kast.manip import flatten_label, free_vars, set_cell
from pyk.kast.prelude.bytes import bytesToken
from pyk.kast.prelude.collections import list_empty, map_empty, map_item, set_empty
from pyk.kast.prelude.k import GENERATED_TOP_CELL
from pyk.kast.prelude.kbool import FALSE, boolToken, notBool
from pyk.kast.prelude.kint import eqInt, intToken, leInt, ltInt
from pyk.kast.prelude.ml import mlEqualsFalse, mlEqualsTrue
from pyk.kast.prelude.utils import token
from pyk.kcfg import KCFG, KCFGExplore
from pyk.kcfg.minimize import KCFGMinimizer
from pyk.kdist import kdist
from pyk.kore.rpc import KoreClient, kore_server
from pyk.proof import ProofStatus
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.utils import hash_str, run_process_2, unique
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn

from .foundry import Foundry, KontrolSemantics, foundry_to_xml
from .options import ConfigType
from .solc_to_k import Contract, decode_kinner_output
from .utils import console, parse_test_version_tuple, replace_k_words

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Final

    from pyk.kast.inner import KInner
    from pyk.kore.rpc import KoreServer

    from .options import ProveOptions
    from .solc_to_k import StorageField

_LOGGER: Final = logging.getLogger(__name__)


def foundry_prove(options: ProveOptions, foundry: Foundry, init_accounts: Iterable[KInner] = ()) -> list[APRProof]:
    if options.workers <= 0:
        raise ValueError(f'Must have at least one worker, found: --workers {options.workers}')
    if options.max_iterations is not None and options.max_iterations < 0:
        raise ValueError(
            f'Must have a non-negative number of iterations, found: --max-iterations {options.max_iterations}'
        )

    if options.use_booster:
        try:
            run_process_2(['which', 'kore-rpc-booster']).stdout.strip()
        except CalledProcessError:
            raise RuntimeError(
                "Couldn't locate the kore-rpc-booster RPC binary. Please put 'kore-rpc-booster' on PATH manually or using kup install/kup shell."
            ) from None

    foundry.mk_proofs_dir(options.reinit, options.remove_old_proofs)

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
        return_empty = options.config_type == ConfigType.SUMMARY_CONFIG
        test_suite = collect_tests(
            foundry, options.tests, reinit=options.reinit, return_empty=return_empty, exact_match=exact_match
        )
        for test in test_suite:
            if not isinstance(test.method, Contract.Method) or test.method.function_calls is None:
                continue
            if not test.contract.has_storage_layout:
                raise RuntimeError(
                    "Couldn't locate 'storageLayout' in the compiled solc output. Please add `extra_output = ['storageLayout']` to your foundry.toml file."
                )

            test_version_tuples = [
                parse_test_version_tuple(t) for t in test.method.function_calls if t not in summary_ids
            ]

            if len(test_version_tuples) > 0:
                _LOGGER.info(f'For test {test.name}, found external calls: {test_version_tuples}')
                new_prove_options = copy(options)
                new_prove_options.tests = test_version_tuples
                new_prove_options.config_type = ConfigType.SUMMARY_CONFIG
                summary_ids.extend(p.id for p in foundry_prove(new_prove_options, foundry, init_accounts))

    exact_match = options.config_type == ConfigType.SUMMARY_CONFIG
    test_suite = collect_tests(foundry, options.tests, reinit=options.reinit, exact_match=exact_match)
    test_names = [test.name for test in test_suite]
    separator = '\n\t\t    '  # ad-hoc separator for the string "Selected functions: " below
    console.print(f'[bold]Selected functions:[/bold] {separator.join(test_names)}')

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
            init_accounts=init_accounts,
        )

    constructor_results: list[APRProof] = []
    if options.run_constructor:
        constructor_tests = collect_constructors(foundry, contracts, reinit=options.reinit)
        constructor_names = [test.name for test in constructor_tests]

        _LOGGER.info(f'Updating digests: {constructor_names}')
        for test in constructor_tests:
            test.method.update_digest(foundry.digest_file)

        if options.verbose:
            _LOGGER.info(f'Running initialization code for contracts in parallel: {constructor_names}')
        else:
            console.print(f'[bold]Running initialization code for contracts in parallel:[/bold] {constructor_names}')

        constructor_results = _run_prover(constructor_tests, include_summaries=False)
        failed = [proof for proof in constructor_results if not proof.passed]
        failed_contract_names = [proof.id.split('.')[0] for proof in failed]
        if failed:
            for proof in failed:
                contract, _ = foundry.get_contract_and_method(proof.id.split(':')[0])
                _interpret_proof_failure(proof, options.failure_info, contract.error_selectors)
            sys.exit(
                f'Running initialization code failed for {len(failed)} contracts: {", ".join(failed_contract_names)}'
            )

    if options.verbose:
        _LOGGER.info(f'Running setup functions in parallel: {setup_method_names}')
    else:
        separator = '\n\t\t\t\t     '  # ad-hoc separator for the string "Running setup functions in parallel: " below
        console.print(f'[bold]Running setup functions in parallel:[/bold] {separator.join(setup_method_names)}')
    setup_results = _run_prover(setup_method_tests, include_summaries=False)

    failed = [proof for proof in setup_results if not proof.passed]
    failed_contract_names = [proof.id.split('.')[0] for proof in failed]
    if failed:
        for proof in failed:
            contract, _ = foundry.get_contract_and_method(proof.id.split(':')[0])
            _interpret_proof_failure(proof, options.failure_info, contract.error_selectors)
        sys.exit(f"Running setUp method failed for {len(failed)} contracts: {', '.join(failed_contract_names)}")

    if options.verbose:
        _LOGGER.info(f'Running test functions in parallel: {test_names}')
    else:
        separator = '\n\t\t\t\t    '  # ad-hoc separator for the string "Running test functions in parallel: " below
        console.print(f'[bold]Running test functions in parallel:[/bold] {separator.join(test_names)}')
    test_results = _run_prover(test_suite, include_summaries=True)

    if options.xml_test_report:
        foundry_to_xml(foundry, constructor_results + setup_results + test_results, options.xml_test_report_name)

    return test_results


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
    init_accounts: Iterable[KInner] = (),
) -> list[APRProof]:
    def init_and_run_proof(test: FoundryTest, progress: Progress | None = None) -> APRFailureInfo | Exception | None:

        task: TaskID | None = None
        if progress is not None:
            task = progress.add_task(
                f'{test.id}',
                total=1,
                status='Loading proof',
                summary='---',
            )

        proof = None
        if Proof.proof_data_exists(test.id, foundry.proofs_dir):
            proof = foundry.get_apr_proof(test.id)
            if proof.passed:
                if progress is not None and task is not None:
                    progress.update(
                        task,
                        status='Finished',
                        summary=proof.one_line_summary,
                        advance=1,
                    )
                return None
        start_time = time.time() if proof is None or proof.status == ProofStatus.PENDING else None

        kore_rpc_command = None
        if isinstance(options.kore_rpc_command, str):
            kore_rpc_command = options.kore_rpc_command.split()

        def select_server() -> OptionalKoreServer:
            if progress is not None and task is not None:
                progress.update(
                    task, status='Starting KoreServer', summary=proof.one_line_summary if proof is not None else '---'
                )
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
                bug_report_id = None if options.bug_report is None else test.id
                client = KoreClient(
                    'localhost',
                    server.port(),
                    bug_report=options.bug_report,
                    bug_report_id=bug_report_id,
                )
                cterm_symbolic = CTermSymbolic(
                    client,
                    foundry.kevm.definition,
                    log_succ_rewrites=options.log_succ_rewrites,
                    log_fail_rewrites=options.log_fail_rewrites,
                )
                return KCFGExplore(
                    cterm_symbolic,
                    kcfg_semantics=KontrolSemantics(auto_abstract_gas=options.auto_abstract_gas),
                    id=test.id,
                )

            if proof is None:
                if progress is not None and task is not None:
                    progress.update(task, status='Initializing proof')
                # With CSE, top-level proof should be a summary if it's not a test or setUp function
                if (
                    (options.cse or options.include_summaries)
                    and options.config_type == ConfigType.TEST_CONFIG
                    and not test.contract.is_test_contract
                ):
                    options.config_type = ConfigType.SUMMARY_CONFIG

                proof = method_to_apr_proof(
                    test=test,
                    foundry=foundry,
                    kcfg_explore=create_kcfg_explore(),
                    bmc_depth=options.bmc_depth,
                    run_constructor=options.run_constructor,
                    init_accounts=init_accounts,
                    summary_ids=summary_ids,
                    active_simbolik=options.with_non_general_state,
                    hevm=options.hevm,
                    config_type=options.config_type,
                    evm_chain_options=EVMChainOptions(
                        {
                            'schedule': options.schedule,
                            'chainid': options.chainid,
                            'mode': options.mode,
                            'usegas': options.usegas,
                        }
                    ),
                    stack_checks=options.stack_checks,
                    symbolic_caller=options.symbolic_caller,
                )
            cut_point_rules = KontrolSemantics.cut_point_rules(
                options.break_on_jumpi,
                options.break_on_jump,
                options.break_on_calls,
                options.break_on_storage,
                options.break_on_basic_blocks,
                options.break_on_load_program,
            )
            if options.break_on_cheatcodes:
                cut_point_rules.extend(
                    rule.label for rule in foundry.kevm.definition.all_modules_dict['FOUNDRY-CHEAT-CODES'].rules
                )
                cut_point_rules.extend(
                    rule.label for rule in foundry.kevm.definition.all_modules_dict['KONTROL-ASSERTIONS'].rules
                )

            lemmas_module = foundry.load_lemmas(options.lemmas)

            if progress is not None and task is not None:
                progress.update(
                    task,
                    status='Running proof',
                    summary=proof.one_line_summary,
                )
            run_prover(
                proof,
                create_kcfg_explore=create_kcfg_explore,
                max_depth=options.max_depth,
                max_iterations=options.max_iterations,
                cut_point_rules=cut_point_rules,
                terminal_rules=KontrolSemantics.terminal_rules(options.break_every_step),
                counterexample_info=options.counterexample_info,
                max_frontier_parallel=options.max_frontier_parallel,
                fail_fast=options.fail_fast,
                force_sequential=options.force_sequential,
                progress=progress,
                task_id=task,
                maintenance_rate=options.maintenance_rate,
                assume_defined=options.assume_defined,
                extra_module=lemmas_module,
                optimize_kcfg=options.optimize_kcfg,
            )

            if progress is not None and task is not None:
                progress.update(task, advance=1, status='Finished')

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

    with Progress(
        SpinnerColumn(),
        TimeElapsedColumn(),
        TextColumn('{task.description}'),
        TextColumn('{task.fields[status]}'),
        TextColumn('{task.fields[summary]}'),
        redirect_stderr=True,
        redirect_stdout=True,
    ) as progress:

        display_status_bar = not (options.hide_status_bar or options.verbose or options.debug)
        failure_infos: list[APRFailureInfo | Exception | None]
        if options.workers > 1 and len(tests) > 1:
            done_tests = 0
            failed_tests = 0
            passed_tests = 0
            if display_status_bar:
                task = progress.add_task(
                    f'Multi-proof Mode ({options.workers} workers)',
                    status='Running',
                    summary=f'{done_tests}/{len(tests)} completed. {passed_tests} passed. {failed_tests} failed.',
                )

            def update_status_bar(test_id: str, result: Any) -> None:
                nonlocal done_tests, failed_tests, passed_tests
                if not display_status_bar or progress is None:
                    return
                done_tests += 1
                proof = foundry.get_apr_proof(test_id)
                if proof.passed:
                    passed_tests += 1
                elif proof.failed:
                    failed_tests += 1
                progress.update(
                    task,
                    summary=f'{done_tests}/{len(tests)} completed. {passed_tests} passed. {failed_tests} failed.',
                )

            with Pool(processes=options.workers) as process_pool:
                results = [
                    process_pool.apply_async(
                        init_and_run_proof, args=(test,), callback=partial(update_status_bar, test.id)
                    )
                    for test in tests
                ]

                process_pool.close()
                process_pool.join()
            if display_status_bar:
                if progress is not None:
                    progress.update(task, status='Finished', advance=1)
            failure_infos = [result.get() for result in results]
        else:
            failure_infos = []
            for test in tests:
                failure_infos.append(init_and_run_proof(test, None if not display_status_bar else progress))

        proofs = [foundry.get_apr_proof(test.id) for test in tests]

        # Reconstruct the proof from the subprocess
        for proof, failure_info in zip(proofs, failure_infos, strict=True):
            assert proof.failure_info is None  # Refactor once this fails
            assert proof.error_info is None
            if isinstance(failure_info, Exception):
                proof.error_info = failure_info
            elif isinstance(failure_info, APRFailureInfo):
                proof.failure_info = KontrolAPRFailureInfo(failure_info)

        return proofs


class KontrolAPRFailureInfo(APRFailureInfo):
    def __init__(self, original: APRFailureInfo):
        self.__dict__.update(original.__dict__)

    def print_with_additional_info(self, status_codes: list[str], outputs: list[str]) -> list[str]:
        res_lines: list[str] = []

        num_pending = len(self.pending_nodes)
        num_failing = len(self.failing_nodes)
        res_lines.append(
            f'{num_pending + num_failing} Failure nodes. ({num_pending} pending and {num_failing} failing)'
        )

        if num_pending > 0:
            res_lines.append('')
            res_lines.append(f'Pending nodes: {sorted(self.pending_nodes)}')

        if num_failing > 0:
            res_lines.append('')
            res_lines.append('Failing nodes:')
            for idx, node_id in enumerate(self.failing_nodes):
                path_condition = self.path_conditions[node_id]
                res_lines.append('')
                res_lines.append(f'  Node id: {str(node_id)}')
                res_lines.append('  Status Code:')
                res_lines.append(f'    {status_codes[idx]}')
                res_lines.append('  Output:')
                res_lines.append(f'    {outputs[idx]}')
                res_lines.append('  Path condition:')
                res_lines += [f'    {path_condition}']

                if node_id in self.models:
                    res_lines.append('  Model:')
                    for var, term in self.models[node_id]:
                        res_lines.append(f'    {var} = {term}')
                else:
                    res_lines.append('  Failed to generate a model.')

            res_lines.append('')
            res_lines.append('Join the Runtime Verification communities for support:')
            res_lines.append('    telegram: https://t.me/rv_kontrol')
            res_lines.append('    discord:  https://discord.gg/CurfmXNtbN')
        return res_lines


def method_to_apr_proof(
    test: FoundryTest,
    foundry: Foundry,
    kcfg_explore: KCFGExplore,
    config_type: ConfigType,
    evm_chain_options: EVMChainOptions,
    stack_checks: bool,
    symbolic_caller: bool,
    bmc_depth: int | None = None,
    run_constructor: bool = False,
    init_accounts: Iterable[KInner] = (),
    summary_ids: Iterable[str] = (),
    active_simbolik: bool = False,
    hevm: bool = False,
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

    kcfg, init_node_id, target_node_id, bounded_node_ids = _method_to_initialized_cfg(
        foundry=foundry,
        test=test,
        kcfg_explore=kcfg_explore,
        setup_proof=setup_proof,
        graft_setup_proof=((setup_proof is not None) and not setup_proof_is_constructor),
        evm_chain_options=evm_chain_options,
        stack_checks=stack_checks,
        symbolic_caller=symbolic_caller,
        init_accounts=init_accounts,
        active_simbolik=active_simbolik,
        hevm=hevm,
        config_type=config_type,
    )

    apr_proof = APRProof(
        test.id,
        kcfg,
        [],
        init_node_id,
        target_node_id,
        {},
        bounded=set(bounded_node_ids),
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
    evm_chain_options: EVMChainOptions,
    stack_checks: bool,
    symbolic_caller: bool,
    *,
    setup_proof: APRProof | None = None,
    graft_setup_proof: bool = False,
    init_accounts: Iterable[KInner] = (),
    active_simbolik: bool = False,
    hevm: bool = False,
) -> tuple[KCFG, int, int, Iterable[int]]:
    _LOGGER.info(f'Initializing KCFG for test: {test.id}')

    empty_config = foundry.kevm.definition.empty_config(GENERATED_TOP_CELL)
    kcfg, new_node_ids, init_node_id, target_node_id, bounded_node_ids = _method_to_cfg(
        foundry,
        empty_config,
        test.contract,
        test.method,
        setup_proof,
        graft_setup_proof,
        evm_chain_options,
        active_simbolik,
        config_type=config_type,
        stack_checks=stack_checks,
        symbolic_caller=symbolic_caller,
        init_accounts=init_accounts,
        hevm=hevm,
    )

    for node_id in new_node_ids:
        _LOGGER.info(f'Expanding macros in node {node_id} for test: {test.name}')
        init_term = kcfg.node(node_id).cterm.kast
        init_term = KDefinition__expand_macros(foundry.kevm.definition, init_term)
        init_cterm = CTerm.from_kast(init_term)
        _LOGGER.info(f'Computing definedness constraint for node {node_id} for test: {test.name}')
        init_cterm, _ = kcfg_explore.cterm_symbolic.simplify(kcfg_explore.cterm_symbolic.assume_defined(init_cterm))
        kcfg.let_node(node_id, cterm=init_cterm)

    _LOGGER.info(f'Expanding macros in target state for test: {test.name}')
    target_term = kcfg.node(target_node_id).cterm.kast
    target_term = KDefinition__expand_macros(foundry.kevm.definition, target_term)
    target_cterm, _ = kcfg_explore.cterm_symbolic.simplify(CTerm.from_kast(target_term))
    kcfg.let_node(target_node_id, cterm=target_cterm)

    return kcfg, init_node_id, target_node_id, bounded_node_ids


def _method_to_cfg(
    foundry: Foundry,
    empty_config: KInner,
    contract: Contract,
    method: Contract.Method | Contract.Constructor,
    setup_proof: APRProof | None,
    graft_setup_proof: bool,
    evm_chain_options: EVMChainOptions,
    active_simbolik: bool,
    config_type: ConfigType,
    stack_checks: bool,
    symbolic_caller: bool,
    init_accounts: Iterable[KInner] = (),
    hevm: bool = False,
) -> tuple[KCFG, list[int], int, int, Iterable[int]]:
    calldata = None
    callvalue = None
    preconditions = None
    external_libs: list[KInner] = []

    if not contract.processed_link_refs:
        external_libs = _process_external_library_references(contract, foundry.contracts)
        if method.is_setup or isinstance(method, Contract.Constructor):
            contract.processed_link_refs = True

    contract_code = bytes.fromhex(contract.deployed_bytecode)
    if isinstance(method, Contract.Constructor):
        program = bytes.fromhex(contract.bytecode)
        callvalue = method.callvalue_cell

    elif isinstance(method, Contract.Method):
        calldata, preconditions = method.constrained_calldata(contract, enums=foundry.enums)
        callvalue = method.callvalue_cell
        program = contract_code

    init_cterm = _init_cterm(
        foundry,
        empty_config,
        contract_name=contract._name,
        program=program,
        contract_code=bytesToken(contract_code),
        storage_fields=contract.fields,
        method=method,
        evm_chain_options=evm_chain_options,
        init_accounts=init_accounts,
        calldata=calldata,
        callvalue=callvalue,
        active_simbolik=active_simbolik,
        config_type=config_type,
        additional_accounts=external_libs,
        stack_checks=stack_checks,
        symbolic_caller=symbolic_caller,
        preconditions=preconditions,
    )
    new_node_ids = []
    bounded_node_ids = []

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
            bounded_node_ids = [node.id for node in setup_proof.bounded]
            cfg = KCFG.from_dict(setup_proof.kcfg.to_dict())
            KCFGMinimizer(cfg).minimize()
            cfg.remove_node(setup_proof.target)
        else:
            cfg = KCFG()
        final_states = [cover.source for cover in setup_proof.kcfg.covers(target_id=setup_proof.target)]
        if not final_states:
            _LOGGER.warning(
                f'Initial state proof {setup_proof.id} for {contract.name_with_path}.{method.signature} has no passing branches to build on. Method will not be executed.'
            )

        # When minimizing constraints, we need to make sure not to forget any variables
        # that might have been instantiated by a branching in the setup KCFG
        keep_vars: set[str] = {
            var
            for split in cfg.splits()
            for _, csubst in split.splits.items()
            for constraint in csubst.constraints
            for var in free_vars(constraint)
        }

        for final_node in final_states:
            new_init_cterm = _update_cterm_from_node(init_cterm, final_node, config_type, keep_vars)
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
        is_setup=method.is_setup,
        hevm=hevm,
        additional_accounts=external_libs,
    )
    target_node = cfg.create_node(final_cterm)

    return cfg, new_node_ids, init_node_id, target_node.id, set(bounded_node_ids)


def _update_cterm_from_node(cterm: CTerm, node: KCFG.Node, config_type: ConfigType, keep_vars: Iterable[str]) -> CTerm:
    if config_type == ConfigType.TEST_CONFIG:
        cell_names = [
            'ACCOUNTS_CELL',
            'NUMBER_CELL',
            'TIMESTAMP_CELL',
            'BASEFEE_CELL',
            'CHAINID_CELL',
            'COINBASE_CELL',
            'PREVCALLER_CELL',
            'PREVORIGIN_CELL',
            'NEWCALLER_CELL',
            'NEWORIGIN_CELL',
            'ACTIVE_CELL',
            'DEPTH_CELL',
            'SINGLECALL_CELL',
            'GAS_CELL',
            'CALLGAS_CELL',
        ]

        cells = {name: node.cterm.cell(name) for name in cell_names}
        all_accounts = flatten_label('_AccountCellMap_', cells['ACCOUNTS_CELL'])

        new_accounts = [CTerm(account, []) for account in all_accounts if (type(account) is KApply and account.is_cell)]
        non_cell_accounts = [account for account in all_accounts if not (type(account) is KApply and account.is_cell)]

        new_accounts_map = {account.cell('ACCTID_CELL'): account for account in new_accounts}

        cells['ACCOUNTS_CELL'] = KEVM.accounts(
            [account.config for account in new_accounts_map.values()] + non_cell_accounts
        )

        new_init_cterm = CTerm(cterm.config, [])

        for cell_name, cell_value in cells.items():
            new_init_cterm = CTerm(set_cell(new_init_cterm.config, cell_name, cell_value), [])

    # config_type == ConfigType.SUMMARY_CONFIG
    # This means that a function is being run in isolation, that is, that the `node` we are
    # taking information from has come from a constructor and not a setUp function.
    # In this case, the <output> cell of the constructor execution becomes the program cell
    # of the function execution and the constraints from the constructor are propagated.
    else:
        new_program_cell = node.cterm.cell('OUTPUT_CELL')
        accounts_cell = cterm.cell('ACCOUNTS_CELL')
        contract_id = cterm.cell('ID_CELL')

        all_accounts = flatten_label('_AccountCellMap_', accounts_cell)
        # TODO: Understand why there are two possible KInner representations or accounts,
        # one directly with `<acccount>` and the other with `AccountCellMapItem`.
        cell_accounts = [
            CTerm(account, []) for account in all_accounts if (type(account) is KApply and account.is_cell)
        ] + [
            CTerm(account.args[1], [])
            for account in all_accounts
            if (type(account) is KApply and account.label.name == 'AccountCellMapItem')
        ]
        other_accounts = [
            account
            for account in all_accounts
            if not (type(account) is KApply and (account.is_cell or account.label.name == 'AccountCellMapItem'))
        ]
        cell_accounts_map = {account.cell('ACCTID_CELL'): account for account in cell_accounts}
        # Set the code of the active contract to the one produced by the constructor
        contract_account = cell_accounts_map[contract_id]
        contract_account = CTerm(set_cell(contract_account.config, 'CODE_CELL', new_program_cell), [])
        cell_accounts_map[contract_id] = contract_account
        new_accounts_cell = KEVM.accounts([account.config for account in cell_accounts_map.values()] + other_accounts)

        new_init_cterm = CTerm(set_cell(cterm.config, 'PROGRAM_CELL', new_program_cell), [])
        new_init_cterm = CTerm(set_cell(new_init_cterm.config, 'ACCOUNTS_CELL', new_accounts_cell), [])

    # Adding constraints from the initial cterm and initial node
    for constraint in cterm.constraints + node.cterm.constraints:
        new_init_cterm = new_init_cterm.add_constraint(constraint)
    new_init_cterm = KEVM.add_invariant(new_init_cterm)

    new_init_cterm = new_init_cterm.remove_useless_constraints(keep_vars)

    return new_init_cterm


def _init_cterm(
    foundry: Foundry,
    empty_config: KInner,
    contract_name: str,
    program: bytes,
    contract_code: KInner,
    storage_fields: tuple[StorageField, ...],
    method: Contract.Method | Contract.Constructor,
    config_type: ConfigType,
    active_simbolik: bool,
    evm_chain_options: EVMChainOptions,
    additional_accounts: list[KInner],
    stack_checks: bool,
    symbolic_caller: bool,
    *,
    calldata: KInner | None = None,
    callvalue: KInner | None = None,
    preconditions: Iterable[KInner] | None = None,
    init_accounts: Iterable[KInner] = (),
) -> CTerm:
    schedule = KApply(evm_chain_options.schedule + '_EVM')
    contract_name = contract_name.upper()

    jumpdests = bytesToken(_process_jumpdests(bytecode=program))
    id_cell = KVariable(Foundry.symbolic_contract_id(contract_name), sort=KSort('Int'))
    init_subst = {
        'MODE_CELL': KApply(evm_chain_options.mode),
        'USEGAS_CELL': boolToken(evm_chain_options.usegas),
        'STACKCHECKS_CELL': boolToken(stack_checks),
        'SCHEDULE_CELL': schedule,
        'CHAINID_CELL': intToken(evm_chain_options.chainid),
        'STATUSCODE_CELL': KVariable('STATUSCODE'),
        'PROGRAM_CELL': bytesToken(program),
        'JUMPDESTS_CELL': jumpdests,
        'ID_CELL': id_cell,
        'CODEADDR_CELL': id_cell,
        'ORIGIN_CELL': KVariable('ORIGIN_ID', sort=KSort('Int')),
        'CALLER_CELL': KVariable('CALLER_ID', sort=KSort('Int')),
        'LOCALMEM_CELL': bytesToken(b''),
        'ACTIVE_CELL': FALSE,
        'DEPTH_CELL': intToken(0),
        'MEMORYUSED_CELL': intToken(0),
        'WORDSTACK_CELL': KApply('.WordStack_EVM-TYPES_WordStack'),
        'PC_CELL': intToken(0),
        'GAS_CELL': KEVM.inf_gas(KVariable('VGAS')),
        'K_CELL': KSequence([KEVM.sharp_execute(), KVariable('CONTINUATION')]),
        'SINGLECALL_CELL': FALSE,
        'ISREVERTEXPECTED_CELL': FALSE,
        'ISOPCODEEXPECTED_CELL': FALSE,
        'RECORDEVENT_CELL': FALSE,
        'EXPECTEDDEPTH_CELL': intToken(0),
        'ISEVENTEXPECTED_CELL': FALSE,
        'ISCALLWHITELISTACTIVE_CELL': FALSE,
        'ISSTORAGEWHITELISTACTIVE_CELL': FALSE,
        'STORAGESLOTLIST_CELL': list_empty(),
        'ALLOWEDCALLSLIST_CELL': list_empty(),
        'MOCKCALLS_CELL': KApply('.MockCallCellMap'),
        'MOCKFUNCTIONS_CELL': KApply('.MockFunctionCellMap'),
    }

    cse_constraints: list[KApply] = []

    if config_type == ConfigType.TEST_CONFIG or active_simbolik:
        init_account_list = (
            _create_initial_account_list(contract_code) + list(additional_accounts) + list(init_accounts)
        )
        origin_id = Foundry.address_DEFAULT_CALLER() if not symbolic_caller else init_subst['ORIGIN_CELL']
        caller_id = Foundry.address_DEFAULT_CALLER() if not symbolic_caller else init_subst['CALLER_CELL']
        init_subst_test = {
            'OUTPUT_CELL': bytesToken(b''),
            'CALLSTACK_CELL': list_empty(),
            'CALLDEPTH_CELL': intToken(0),
            'ID_CELL': Foundry.address_TEST_CONTRACT(),
            'CODEADDR_CELL': Foundry.address_TEST_CONTRACT(),
            'ORIGIN_CELL': origin_id,
            'CALLER_CELL': caller_id,
            'LOG_CELL': list_empty(),
            'ACCESSEDACCOUNTS_CELL': set_empty(),
            'ACCESSEDSTORAGE_CELL': map_empty(),
            'INTERIMSTATES_CELL': list_empty(),
            'TOUCHEDACCOUNTS_CELL': set_empty(),
            'CREATEDACCOUNTS_CELL': set_empty(),
            'STATIC_CELL': FALSE,
            'ACCOUNTS_CELL': KEVM.accounts(init_account_list),
        }
        init_subst.update(init_subst_test)
    else:
        # CSE needs to be agnostic of the following Kontrol cells
        del init_subst['ACTIVE_CELL']
        del init_subst['ISEVENTEXPECTED_CELL']
        del init_subst['ISREVERTEXPECTED_CELL']
        del init_subst['RECORDEVENT_CELL']
        del init_subst['SINGLECALL_CELL']

        accounts: list[KInner] = []
        contract_account_name = Foundry.symbolic_contract_name(contract_name)

        if isinstance(method, Contract.Constructor):
            # Symbolic account for the contract being executed
            accounts.append(Foundry.symbolic_account(contract_account_name, contract_code))
        else:
            # Symbolic accounts of all relevant contracts
            accounts, cse_constraints = _create_cse_accounts(
                foundry, storage_fields, contract_account_name, contract_code
            )

        accounts.append(KVariable('ACCOUNTS_REST', sort=KSort('AccountCellMap')))

        init_subst_accounts = {'ACCOUNTS_CELL': KEVM.accounts(accounts)}
        init_subst.update(init_subst_accounts)

        # For purposes of summarization, assume we will call in a static context when the method isn't
        # explicitly marked as method or view. If it is called in a static context, the summary simply won't
        # apply.
        if not isinstance(method, Contract.Constructor) and not (method.view or method.pure):
            init_subst['STATIC_CELL'] = FALSE

        # TODO:
        # andBool notBool (ACTIVE_CELL orBool PRAKNDEPTH_CELL >=Int CALLDEPTH_CELL)
        # andBool notBool (EXPECTED_REVERT_CELL orBool REVERTDEPTH_CELL >=Int CALLDEPTH_CELL)

        # Assume we're not in an active prank context
        inactive_prank_constraint = mlEqualsTrue(
            notBool(
                KApply(
                    '_orBool_',
                    [
                        KVariable('ACTIVE_CELL', sort=KSort('Bool')),
                        KApply(
                            '_>=Int_',
                            [
                                KVariable('DEPTH_CELL', sort=KSort('Int')),
                                KVariable('CALLDEPTH_CELL', sort=KSort('Int')),
                            ],
                        ),
                    ],
                )
            )
        )
        inactive_expect_revert_constraint = mlEqualsTrue(
            notBool(
                KApply(
                    '_orBool_',
                    [
                        KVariable('ISREVERTEXPECTED_CELL', sort=KSort('Bool')),
                        KApply(
                            '_>=Int_',
                            [
                                KVariable('EXPECTEDDEPTH_CELL', sort=KSort('Int')),
                                KVariable('CALLDEPTH_CELL', sort=KSort('Int')),
                            ],
                        ),
                    ],
                )
            )
        )
        cse_constraints += [
            inactive_prank_constraint,
            inactive_expect_revert_constraint,
        ]

    if calldata is not None:
        init_subst['CALLDATA_CELL'] = calldata

    if callvalue is not None:
        init_subst['CALLVALUE_CELL'] = callvalue

    if not evm_chain_options.usegas:
        init_subst['GAS_CELL'] = intToken(0)
        init_subst['CALLGAS_CELL'] = intToken(0)
        init_subst['REFUND_CELL'] = intToken(0)

    if isinstance(method, Contract.Constructor):
        # constructor can not be called in a static context.
        init_subst['STATIC_CELL'] = FALSE

        encoded_args, arg_constraints = method.encoded_args(foundry.enums)
        init_subst['PROGRAM_CELL'] = KEVM.bytes_append(bytesToken(program), encoded_args)

    init_term = Subst(init_subst)(empty_config)
    init_cterm = CTerm.from_kast(init_term)

    if preconditions is not None:
        for precondition in preconditions:
            init_cterm = init_cterm.add_constraint(mlEqualsTrue(precondition))
    for constraint in cse_constraints:
        init_cterm = init_cterm.add_constraint(constraint)

    non_cheatcode_contract_ids = []
    if not (config_type == ConfigType.TEST_CONFIG or active_simbolik):
        non_cheatcode_contract_ids = [Foundry.symbolic_contract_id(contract_name), 'CALLER_ID', 'ORIGIN_ID']
        # The calling contract is assumed to be in the present accounts for non-tests
        init_cterm.add_constraint(
            mlEqualsTrue(
                KApply(
                    '_in_keys(_)_MAP_Bool_KItem_Map',
                    [KVariable('CALLER_ID', sort=KSort('Int')), init_cterm.cell('ACCOUNTS_CELL')],
                )
            )
        )
    elif symbolic_caller:
        non_cheatcode_contract_ids = ['CALLER_ID', 'ORIGIN_ID']

    for contract_id in non_cheatcode_contract_ids:
        # The address of the executing contract, the calling contract, and the origin contract
        # are always guaranteed to not be the address of the cheatcode contract
        init_cterm = init_cterm.add_constraint(
            mlEqualsFalse(KApply('_==Int_', [KVariable(contract_id, sort=KSort('Int')), Foundry.address_CHEATCODE()]))
        )

    if isinstance(method, Contract.Constructor) and len(arg_constraints) > 0:
        for arg_constraint in arg_constraints:
            init_cterm = init_cterm.add_constraint(mlEqualsTrue(arg_constraint))

    init_cterm = KEVM.add_invariant(init_cterm)

    return init_cterm


def _create_initial_account_list(program: KInner) -> list[KInner]:
    _contract = KEVM.account_cell(
        Foundry.address_TEST_CONTRACT(),
        intToken(79228162514264337593543950335),
        program,
        map_empty(),
        map_empty(),
        map_empty(),
        intToken(1),
    )
    init_account_list: list[KInner] = [
        _contract,
        Foundry.account_CHEATCODE_ADDRESS(map_empty()),
    ]
    return init_account_list


def _create_cse_accounts(
    foundry: Foundry,
    storage_fields: tuple[StorageField, ...],
    contract_name: str,
    contract_code: KInner,
) -> tuple[list[KInner], list[KApply]]:
    """
    Recursively generates a list of new accounts corresponding to `contract` fields, each having <code> and <storage> cell (partially) set up.
    Args:
        foundry (Foundry): The Foundry object containing the information about contracts in the project.
        storage_fields (tuple[StorageField, ...]): A tuple of StorageField objects representing the contract's storage fields.
        contract_name (str): The name of the contract being executed to be used in the account-related symbolic variables.
        contract_code (KInner): The KInner object representing the contract's runtime bytecode.
    Returns:
        tuple[list[KInner], list[KApply]]:
            - A list of accounts to be included in the initial configuration.
            - A list of constraints on symbolic account IDs.
    """

    def extend_storage(map: KInner, slot: int, value: KInner) -> KInner:
        return KApply('_Map_', [map_item(intToken(slot), value), map])

    new_accounts: list[KInner] = []
    new_account_constraints: list[KApply] = []

    storage_map: KInner = KVariable(contract_name + '_STORAGE', sort=KSort('Map'))

    singly_occupied_slots = [
        slot for (slot, count) in Counter(field.slot for field in storage_fields).items() if count == 1
    ]

    for field in storage_fields:
        field_name = contract_name + '_' + field.label.upper()
        if field.data_type.startswith('enum'):
            enum_name = field.data_type.split(' ')[1]
            if enum_name not in foundry.enums:
                _LOGGER.info(
                    f'Skipping adding constraint for {enum_name} because it is not tracked by Kontrol. It can be automatically constrained to its possible values by adding --enum-constraints.'
                )
            else:
                enum_max = foundry.enums[enum_name]
                new_account_constraints.append(
                    mlEqualsTrue(
                        ltInt(
                            KEVM.lookup(storage_map, intToken(field.slot)),
                            intToken(enum_max),
                        )
                    )
                )
        # Processing of strings
        if field.data_type == 'string':
            string_contents = KVariable(field_name + '_S_CONTENTS', sort=KSort('Bytes'))
            string_length = KVariable(field_name + '_S_LENGTH', sort=KSort('Int'))
            string_structure = KEVM.as_word(
                KApply(
                    '_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                    [
                        string_contents,
                        KEVM.buf(
                            intToken(1),
                            KApply('_*Int_', [intToken(2), string_length]),
                        ),
                    ],
                )
            )
            string_contents_length = eqInt(KEVM.size_bytes(string_contents), intToken(31))
            string_length_lb = leInt(intToken(0), string_length)
            string_length_ub = ltInt(string_length, intToken(32))

            storage_map = extend_storage(storage_map, field.slot, string_structure)
            new_account_constraints.append(mlEqualsTrue(string_contents_length))
            new_account_constraints.append(mlEqualsTrue(string_length_lb))
            new_account_constraints.append(mlEqualsTrue(string_length_ub))
        # Processing of addresses
        if field.data_type == 'address':
            if field.slot in singly_occupied_slots:
                # The offset must equal zero
                assert field.offset == 0
                # Create appropriate symbolic variable
                field_variable = KVariable(field_name + '_ID', sort=KSort('Int'))
                # Update storage map accordingly: ( field.slot |-> contract_account_variable ) STORAGE_MAP
                storage_map = extend_storage(storage_map, field.slot, field_variable)
                address_range_lb = leInt(intToken(0), field_variable)
                address_range_ub = ltInt(field_variable, intToken(1461501637330902918203684832716283019655932542976))
                new_account_constraints.append(mlEqualsTrue(address_range_lb))
                new_account_constraints.append(mlEqualsTrue(address_range_ub))
        # Processing of contracts
        if field.data_type.startswith('contract '):
            if field.linked_interface:
                contract_type = field.linked_interface
            else:
                contract_type = field.data_type.split(' ')[1]
            for full_contract_name, contract_obj in foundry.contracts.items():
                # TODO: this is not enough, it is possible that the same contract comes with
                # src% and test%, in which case we don't know automatically which one to choose
                if full_contract_name.split('%')[-1] == contract_type:
                    contract_account_code = bytesToken(bytes.fromhex(contract_obj.deployed_bytecode))
                    contract_account_variable = KVariable(field_name + '_ID', sort=KSort('Int'))

                    # New contract account is not the cheatcode contract
                    new_account_constraints.append(
                        mlEqualsFalse(
                            KApply(
                                '_==Int_',
                                [
                                    contract_account_variable,
                                    Foundry.address_CHEATCODE(),
                                ],
                            )
                        )
                    )
                    # The contract address must occupy the entire slot
                    if field.slot in singly_occupied_slots:
                        # The offset must equal zero
                        assert field.offset == 0
                        # Update storage map accordingly: ( field.slot |-> contract_account_variable ) STORAGE_MAP
                        storage_map = KApply(
                            '_Map_', [map_item(intToken(field.slot), contract_account_variable), storage_map]
                        )
                    else:
                        slot_var_before = KVariable(f'{field_name}_SLOT_BEFORE', sort=KSort('Bytes'))
                        slot_var_after = KVariable(f'{field_name}_SLOT_AFTER', sort=KSort('Bytes'))
                        masked_contract_account_var = KApply(
                            'asWord',
                            [
                                KApply(
                                    '_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                                    [
                                        slot_var_before,
                                        KApply(
                                            '_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                                            [
                                                KEVM.buf(intToken(20), contract_account_variable),
                                                slot_var_after,
                                            ],
                                        ),
                                    ],
                                )
                            ],
                        )
                        storage_map = KApply(
                            '_Map_', [map_item(intToken(field.slot), masked_contract_account_var), storage_map]
                        )
                        new_account_constraints.append(
                            mlEqualsTrue(
                                KApply(
                                    '_==K_',
                                    [
                                        KApply(
                                            'lengthBytes(_)_BYTES-HOOKED_Int_Bytes',
                                            [slot_var_after],
                                        ),
                                        intToken(field.offset),
                                    ],
                                )
                            )
                        )
                        new_account_constraints.append(
                            mlEqualsTrue(
                                KApply(
                                    '_==K_',
                                    [
                                        KApply(
                                            'lengthBytes(_)_BYTES-HOOKED_Int_Bytes',
                                            [slot_var_before],
                                        ),
                                        intToken(32 - 20 - field.offset),
                                    ],
                                )
                            )
                        )

                    contract_accounts, contract_constraints = _create_cse_accounts(
                        foundry, contract_obj.fields, field_name, contract_account_code
                    )
                    new_accounts.extend(contract_accounts)
                    new_account_constraints.extend(contract_constraints)

    # In this way, we propagate the storage updates from the iterations
    new_accounts.append(Foundry.symbolic_account(contract_name, contract_code, storage_map))

    return new_accounts, new_account_constraints


def _final_cterm(
    empty_config: KInner,
    program: KInner,
    config_type: ConfigType,
    additional_accounts: list[KInner],
    *,
    failing: bool,
    is_test: bool = True,
    is_setup: bool = False,
    hevm: bool = False,
) -> CTerm:
    final_term = _final_term(empty_config, program, additional_accounts, config_type=config_type)
    dst_failed_post = KEVM.lookup(KVariable('CHEATCODE_STORAGE_FINAL'), Foundry.loc_FOUNDRY_FAILED())
    final_cterm = CTerm.from_kast(final_term)
    if is_test or is_setup:
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
                        Foundry.hevm_success(KVariable('STATUSCODE_FINAL'), dst_failed_post, KVariable('OUTPUT_FINAL'))
                    )
                )
            else:
                # To do: Print warning to the user
                return final_cterm.add_constraint(
                    mlEqualsTrue(Foundry.hevm_fail(KVariable('STATUSCODE_FINAL'), dst_failed_post))
                )

    return final_cterm


def _final_term(
    empty_config: KInner, program: KInner, additional_accounts: list[KInner], config_type: ConfigType
) -> KInner:
    post_account_cell = KEVM.account_cell(
        Foundry.address_TEST_CONTRACT(),
        KVariable('ACCT_BALANCE_FINAL'),
        program,
        KVariable('ACCT_STORAGE_FINAL'),
        KVariable('ACCT_ORIGSTORAGE_FINAL'),
        KVariable('ACCT_TRANSIENTSTORAGE_FINAL'),
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
        'ALLOWEDCALLSLIST_CELL': KVariable('ALLOWEDCALLSLIST_FINAL'),
        'STORAGESLOTLIST_CELL': KVariable('STORAGESLOTLIST_FINAL'),
    }

    if config_type == ConfigType.TEST_CONFIG:
        account_list: list[KInner] = [
            post_account_cell,
            Foundry.account_CHEATCODE_ADDRESS(KVariable('CHEATCODE_STORAGE_FINAL')),
        ]
        account_list.extend(additional_accounts)
        account_list.append(KVariable('ACCOUNTS_FINAL'))
        final_subst_test = {
            'ID_CELL': Foundry.address_TEST_CONTRACT(),
            'CODEADDR_CELL': Foundry.address_TEST_CONTRACT(),
            'ACCOUNTS_CELL': KEVM.accounts(account_list),
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
            KVariable('ADDRESSLIST_FINAL'),
            KVariable('STORAGESLOTLIST_FINAL'),
        ],
    )


def _process_external_library_references(contract: Contract, foundry_contracts: dict[str, Contract]) -> list[KInner]:
    """Create a list of KInner accounts for external libraries used in the given contract.

    This function identifies external library placeholders within the contract's bytecode and deployed bytecode,
    deploys the required external libraries at the address generated based on the first 20 bytes of the hash of the
    unique id, replaces the placeholders with the actual addresses of the deployed libraries, and returns a list of
    KEVM account cells representing the deployed external libraries.

    :param contract: The contract object containing the deployed bytecode and external library references.
    :param foundry_contracts: A dictionary mapping library names to Contract instances, representing all
                             available contracts including external libraries.
    :raises ValueError: If an external library referenced in the contract's bytecode is not found in foundry_contracts.
    :return:  A list of KEVM account cells representing the deployed external libraries.
    """
    external_libs: list[KInner] = []
    address_list: dict[str, str] = {}

    for ref_type in ['bytecode_external_lib_refs', 'deployed_bytecode_external_lib_refs']:
        lib_refs = getattr(contract, ref_type, {})

        for lib, ref_locations in lib_refs.items():
            ref_contract = foundry_contracts.get(lib)
            if ref_contract is None:
                raise ValueError(f'External library not found: {lib}')

            if lib not in address_list:
                new_address_hex = hash_str(lib)[:40].ljust(40, '0')
                new_address_int = int(new_address_hex, 16)
                _LOGGER.info(f'Deploying external library {lib} at address 0x{new_address_hex}')

                # `deployed_bytecode` libraries are a subset of `bytecode` libraries
                if ref_contract.bytecode_external_lib_refs:
                    external_libs.extend(_process_external_library_references(ref_contract, foundry_contracts))

                ref_code = token(bytes.fromhex(ref_contract.deployed_bytecode))
                external_libs.append(
                    KEVM.account_cell(
                        id=token(new_address_int),
                        balance=token(0),
                        code=ref_code,
                        storage=map_empty(),
                        orig_storage=map_empty(),
                        transient_storage=map_empty(),
                        nonce=token(0),
                    )
                )
                address_list[lib] = new_address_hex
            else:
                new_address_hex = address_list[lib]

            bytecode_field = 'bytecode' if ref_type == 'bytecode_external_lib_refs' else 'deployed_bytecode'

            for ref_start, ref_len in ref_locations:
                placeholder_start = ref_start * 2
                placeholder_len = ref_len * 2

                current_bytecode = getattr(contract, bytecode_field)
                updated_bytecode = (
                    current_bytecode[:placeholder_start]
                    + new_address_hex
                    + current_bytecode[placeholder_start + placeholder_len :]
                )
                setattr(contract, bytecode_field, updated_bytecode)

    return external_libs


def _interpret_proof_failure(
    proof: APRProof, failure_info: bool, contract_error_selectors: dict[bytes, tuple[str, list[str]]]
) -> None:
    failure_log = None
    if isinstance(proof, APRProof) and isinstance(proof.failure_info, KontrolAPRFailureInfo):
        failure_log = proof.failure_info
    if failure_info and failure_log is not None:
        status_codes: list[str] = []
        output_values: list[str] = []
        kevm = KEVM(kdist.get('kontrol.base'))
        for node_id in failure_log.failing_nodes:
            node = proof.kcfg.get_node(node_id)
            assert node is not None
            output_cell = node.cterm.cell('OUTPUT_CELL')
            output_pretty = kevm.pretty_print(output_cell)
            status_codes.append(kevm.pretty_print(node.cterm.cell('STATUSCODE_CELL')))
            output_values.append(decode_kinner_output(output_cell, output_pretty, contract_error_selectors))
        log = failure_log.print_with_additional_info(status_codes, output_values) + Foundry.help_info()
        for line in log:
            print(replace_k_words(line))
