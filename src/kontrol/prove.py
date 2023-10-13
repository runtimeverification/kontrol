from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from queue import Queue
from subprocess import CalledProcessError
from threading import Thread
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
from pyk.kore.rpc import kore_server
from pyk.prelude.k import GENERATED_TOP_CELL
from pyk.prelude.kbool import FALSE, notBool
from pyk.prelude.kint import intToken
from pyk.prelude.ml import mlEqualsTrue
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRBMCProof, APRBMCProver, APRProof, APRProver
from pyk.proof.show import APRProofShow
from pyk.utils import run_process, single, unique
from pyk.proof.reachability import APRBMCProof, APRProof
from pyk.utils import run_process, unique

from .foundry import Foundry
from .solc_to_k import Contract

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
    from typing import Final

    from pyk.kast.inner import KInner
    from pyk.kcfg import KCFGExplore
    from pyk.kcfg.explore import ExtendResult
    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport


_LOGGER: Final = logging.getLogger(__name__)


def foundry_prove(
    foundry_root: Path,
    max_depth: int = 1000,
    max_iterations: int | None = None,
    reinit: bool = False,
    tests: Iterable[tuple[str, int | None]] = (),
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
    run_constructor: bool = False,
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

    contracts = [test.contract for test in test_suite]
    setup_method_tests = collect_setup_methods(foundry, contracts, reinit=reinit)
    setup_method_names = [test.name for test in setup_method_tests]

    constructor_tests = collect_constructors(foundry, contracts, reinit=reinit)
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

    def run_prover(test_suite: list[FoundryTest]) -> dict[tuple[str, int], tuple[bool, list[str] | None]]:
        llvm_definition_dir = foundry.llvm_library if use_booster else None

        options = GlobalOptions(
            foundry=foundry,
            auto_abstract_gas=auto_abstract_gas,
            bug_report=bug_report,
            kore_rpc_command=kore_rpc_command,
            llvm_definition_dir=llvm_definition_dir,
            smt_timeout=smt_timeout,
            smt_retry_limit=smt_retry_limit,
            trace_rewrites=trace_rewrites,
            simplify_init=simplify_init,
            bmc_depth=bmc_depth,
            max_depth=max_depth,
            break_every_step=break_every_step,
            break_on_jumpi=break_on_jumpi,
            break_on_calls=break_on_calls,
            workers=workers,
            counterexample_info=counterexample_info,
            max_iterations=max_iterations,
            run_constructor=run_constructor,
        )

        scheduler = Scheduler(workers=workers, initial_tests=test_suite, options=options)
        scheduler.run()

        return scheduler.results

    #          return _run_cfg_group(
    #              test_suite,
    #              foundry,
    #              max_depth=max_depth,
    #              max_iterations=max_iterations,
    #              workers=workers,
    #              simplify_init=simplify_init,
    #              break_every_step=break_every_step,
    #              break_on_jumpi=break_on_jumpi,
    #              break_on_calls=break_on_calls,
    #              bmc_depth=bmc_depth,
    #              bug_report=bug_report,
    #              kore_rpc_command=kore_rpc_command,
    #              use_booster=use_booster,
    #              smt_timeout=smt_timeout,
    #              smt_retry_limit=smt_retry_limit,
    #              counterexample_info=counterexample_info,
    #              trace_rewrites=trace_rewrites,
    #              auto_abstract_gas=auto_abstract_gas,
    #              port=port,
    #          )

    if run_constructor:
        _LOGGER.info(f'Running initialization code for contracts in parallel: {constructor_names}')
        results = run_prover(constructor_tests)
        failed = [init_cfg for init_cfg, passed in results.items() if not passed]
        if failed:
            raise ValueError(f'Running initialization code failed for {len(failed)} contracts: {failed}')

    _LOGGER.info(f'Running setup functions in parallel: {setup_method_names}')
    results = run_prover(setup_method_tests)

    failed = [setup_cfg for setup_cfg, passed in results.items() if not passed]
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


class Job(ABC):
    @abstractmethod
    def execute(self, queue: Queue, done_queue: Queue) -> None:
        ...


class InitProofJob(Job):
    test: FoundryTest
    proof: APRProof
    options: GlobalOptions
    port: int

    def __init__(
        self,
        test: FoundryTest,
        options: GlobalOptions,
        port: int,
    ) -> None:
        self.test = test
        self.options = options
        self.port = port

    def execute(self, queue: Queue, done_queue: Queue) -> None:
        with legacy_explore(
            self.options.foundry.kevm,
            kcfg_semantics=KEVMSemantics(auto_abstract_gas=self.options.auto_abstract_gas),
            id=self.test.id,
            bug_report=self.options.bug_report,
            kore_rpc_command=self.options.kore_rpc_command,
            llvm_definition_dir=self.options.llvm_definition_dir,
            smt_timeout=self.options.smt_timeout,
            smt_retry_limit=self.options.smt_retry_limit,
            trace_rewrites=self.options.trace_rewrites,
            start_server=False,
            port=self.port,
        ) as kcfg_explore:
            self.proof = method_to_apr_proof(
                self.options.foundry,
                self.test,
                kcfg_explore,
                simplify_init=self.options.simplify_init,
                bmc_depth=self.options.bmc_depth,
                run_constructor=self.options.run_constructor,
            )
            self.proof.write_proof_data()
            for pending_node in self.proof.pending:
                done_queue.put(
                    AdvanceProofJob(
                        test=self.test, node_id=pending_node.id, proof=self.proof, options=self.options, port=self.port
                    )
                )


@dataclass
class GlobalOptions:
    foundry: Foundry
    auto_abstract_gas: bool
    bug_report: BugReport | None
    kore_rpc_command: str | Iterable[str] | None
    llvm_definition_dir: Path | None
    smt_timeout: int | None
    smt_retry_limit: int | None
    trace_rewrites: bool
    simplify_init: bool
    bmc_depth: int | None
    max_depth: int
    break_every_step: bool
    break_on_jumpi: bool
    break_on_calls: bool
    workers: int
    counterexample_info: bool
    max_iterations: int | None
    run_constructor: bool


class AdvanceProofJob(Job):
    test: FoundryTest
    proof: APRProof
    options: GlobalOptions
    node_id: int
    port: int

    def __init__(
        self,
        test: FoundryTest,
        node_id: int,
        proof: APRProof,
        options: GlobalOptions,
        port: int,
    ) -> None:
        self.test = test
        self.node_id = node_id
        self.proof = proof
        self.options = options
        self.port = port

    def execute(self, queue: Queue, done_queue: Queue) -> None:
        with legacy_explore(
            self.options.foundry.kevm,
            kcfg_semantics=KEVMSemantics(auto_abstract_gas=self.options.auto_abstract_gas),
            id=self.test.id,
            bug_report=self.options.bug_report,
            kore_rpc_command=self.options.kore_rpc_command,
            llvm_definition_dir=self.options.llvm_definition_dir,
            smt_timeout=self.options.smt_timeout,
            smt_retry_limit=self.options.smt_retry_limit,
            trace_rewrites=self.options.trace_rewrites,
            start_server=False,
            port=self.port,
        ) as kcfg_explore:
            curr_node = self.proof.kcfg.node(self.node_id)
            terminal_rules = build_terminal_rules(options=self.options)
            cut_point_rules = build_cut_point_rules(options=self.options)
            #              prover = build_prover(options=self.options, proof=self.proof, kcfg_explore=kcfg_explore)
            #              assert type(prover) is APRProver

            cterm = curr_node.cterm

            extend_result = kcfg_explore.extend_cterm(
                cterm,
                execute_depth=self.options.max_depth,
                cut_point_rules=cut_point_rules,
                terminal_rules=terminal_rules,
            )
            print(f'pushing ExtendKCFGJob to done_queue {self.test.id} {curr_node.id}')
            done_queue.put(
                ExtendKCFGJob(
                    test=self.test,
                    proof=self.proof,
                    node_id=curr_node.id,
                    port=self.port,
                    extend_result=extend_result,
                    options=self.options,
                )
            )


class ExtendKCFGJob(Job):
    options: GlobalOptions
    test: FoundryTest
    node_id: int
    proof: APRProof
    port: int
    extend_result: ExtendResult

    def __init__(
        self,
        test: FoundryTest,
        proof: APRProof,
        node_id: int,
        port: int,
        extend_result: ExtendResult,
        options: GlobalOptions,
    ) -> None:
        self.test = test
        self.proof = proof
        self.node_id = node_id
        self.port = port
        self.options = options
        self.extend_result = extend_result

    def execute(self, queue: Queue, done_queue: Queue) -> None:
        with legacy_explore(
            self.options.foundry.kevm,
            kcfg_semantics=KEVMSemantics(auto_abstract_gas=self.options.auto_abstract_gas),
            id=self.test.id,
            bug_report=self.options.bug_report,
            kore_rpc_command=self.options.kore_rpc_command,
            llvm_definition_dir=self.options.llvm_definition_dir,
            smt_timeout=self.options.smt_timeout,
            smt_retry_limit=self.options.smt_retry_limit,
            trace_rewrites=self.options.trace_rewrites,
            start_server=False,
            port=self.port,
        ) as kcfg_explore:
            proof_show = APRProofShow(kprint=self.options.foundry.kevm)
            print('\n'.join(proof_show.show(self.proof)))

            kcfg_explore.extend_kcfg(
                self.extend_result,
                kcfg=self.proof.kcfg,
                node=self.proof.kcfg.node(self.node_id),
                logs=self.proof.logs,
            )

            print('\n'.join(proof_show.show(self.proof)))


def create_server(options: GlobalOptions) -> KoreServer:
    return kore_server(
        definition_dir=options.foundry.kevm.definition_dir,
        llvm_definition_dir=options.llvm_definition_dir,
        module_name=options.foundry.kevm.main_module,
        command=options.kore_rpc_command,
        bug_report=options.bug_report,
        smt_timeout=options.smt_timeout,
        smt_retry_limit=options.smt_retry_limit,
    )


class Scheduler:
    servers: dict[str, KoreServer]
    proofs: dict[FoundryTest, APRProof]
    threads: list[Thread]
    task_queue: Queue
    done_queue: Queue
    options: GlobalOptions
    iterations: dict[str, int]

    results: dict[tuple[str, int], tuple[bool, list[str] | None]]

    job_counter: int

    @staticmethod
    def exec_process(task_queue: Queue, done_queue: Queue) -> None:
        while True:
            job = task_queue.get()
            job.execute(task_queue, done_queue)
            task_queue.task_done()

    def __init__(self, workers: int, initial_tests: list[FoundryTest], options: GlobalOptions) -> None:
        self.options = options
        self.task_queue = Queue()
        self.done_queue = Queue()
        self.servers = {}
        self.results = {}
        self.iterations = {}
        self.job_counter = 0
        self.done_counter = 0
        for test in initial_tests:
            self.servers[test.id] = create_server(self.options)
            self.task_queue.put(InitProofJob(test=test, port=self.servers[test.id].port, options=self.options))
            self.iterations[test.id] = 0
            print(f'adding InitProofJob {test.id}')
            self.job_counter += 1
        self.threads = [
            Thread(target=Scheduler.exec_process, args=(self.task_queue, self.done_queue), daemon=True)
            for i in range(self.options.workers)
        ]

    def run(self) -> None:
        for thread in self.threads:
            print('starting thread')
            thread.start()
        while self.job_counter > 0:
            result = self.done_queue.get()
            self.job_counter -= 1
            if type(result) is AdvanceProofJob:
                print('result is AdvanceProofJob')
                print(f'pulled AdvanceProofJob {result.test.id} {result.node_id}')
                self.task_queue.put(result)
                print(f'pushing AdvanceProofJob {result.test.id} {result.node_id}')
                self.job_counter += 1
            elif type(result) is ExtendKCFGJob:
                if (
                    self.options.max_iterations is not None
                    and self.options.max_iterations <= self.iterations[result.test.id]
                ):
                    _LOGGER.warning(f'Reached iteration bound {result.proof.id}: {self.options.max_iterations}')
                    break
                self.iterations[result.test.id] += 1

                print(f'pulled ExtendKCFGJob {result.test.id} {result.node_id}')

                result.execute(self.task_queue, self.done_queue)

                with legacy_explore(
                    self.options.foundry.kevm,
                    kcfg_semantics=KEVMSemantics(auto_abstract_gas=self.options.auto_abstract_gas),
                    id=result.test.id,
                    bug_report=self.options.bug_report,
                    kore_rpc_command=self.options.kore_rpc_command,
                    llvm_definition_dir=self.options.llvm_definition_dir,
                    smt_timeout=self.options.smt_timeout,
                    smt_retry_limit=self.options.smt_retry_limit,
                    trace_rewrites=self.options.trace_rewrites,
                    start_server=False,
                    port=result.port,
                ) as kcfg_explore:
                    prover = build_prover(options=self.options, proof=result.proof, kcfg_explore=kcfg_explore)
                    prover._check_all_terminals()

                    for node in result.proof.terminal:
                        if result.proof.kcfg.is_leaf(node.id) and not result.proof.is_target(node.id):
                            # TODO can we have a worker thread check subsumtion?
                            prover._check_subsume(node)

                    result.proof.write_proof_data()

                    if not result.proof.pending:
                        failure_log = None
                        if not result.proof.passed:
                            failure_log = print_failure_info(
                                result.proof, kcfg_explore, self.options.counterexample_info
                            )
                        self.results[(result.test.id, result.test.version)] = (result.proof.passed, failure_log)

                    for pending_node in result.proof.pending:
                        if pending_node not in result.proof.kcfg.reachable_nodes(source_id=result.node_id):
                            continue
                        print(f'pushing AdvanceProofJob {result.test.id} {pending_node.id}')
                        self.task_queue.put(
                            AdvanceProofJob(
                                test=result.test,
                                node_id=pending_node.id,
                                proof=result.proof,
                                options=self.options,
                                port=result.port,
                            )
                        )
                        self.job_counter += 1

        print('a')
        self.task_queue.join()
        print('b')


def build_terminal_rules(
    options: GlobalOptions,
) -> list[str]:
    terminal_rules = ['EVM.halt']
    if options.break_every_step:
        terminal_rules.append('EVM.step')
    return terminal_rules


def build_cut_point_rules(
    options: GlobalOptions,
) -> list[str]:
    cut_point_rules = []
    if options.break_on_jumpi:
        cut_point_rules.extend(['EVM.jumpi.true', 'EVM.jumpi.false'])
    if options.break_on_calls:
        cut_point_rules.extend(
            [
                'EVM.call',
                'EVM.callcode',
                'EVM.delegatecall',
                'EVM.staticcall',
                'EVM.create',
                'EVM.create2',
                'FOUNDRY.foundry.call',
                'EVM.end',
                'EVM.return.exception',
                'EVM.return.revert',
                'EVM.return.success',
            ]
        )
    return cut_point_rules


def build_prover(
    options: GlobalOptions,
    proof: Proof,
    kcfg_explore: KCFGExplore,
    # ) -> Prover
) -> APRProver:
    proof = proof
    if type(proof) is APRBMCProof:
        return APRBMCProver(proof, kcfg_explore)
    elif type(proof) is APRProof:
        return APRProver(proof, kcfg_explore)
    #      elif type(proof) is EqualityProof:
    #          return EqualityProver(kcfg_explore=kcfg_explore, proof=proof)
    else:
        raise ValueError(f'Do not know how to build prover for proof: {proof}')


def collect_constructors(foundry: Foundry, contracts: Iterable[Contract] = (), *, reinit: bool) -> list[FoundryTest]:
    res: list[FoundryTest] = []
    contract_names: set[str] = set()  # ensures uniqueness of each result (Contract itself is not hashable)
    for contract in contracts:
        if contract.name in contract_names:
            continue
        contract_names.add(contract.name)

        method = contract.constructor
        if not method:
            continue
        version = foundry.resolve_proof_version(f'{contract.name}.init', reinit, None)
        res.append(FoundryTest(contract, method, version))
    return res


def _run_cfg_group(
    tests: list[FoundryTest],
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
    run_constructor: bool = False,
) -> dict[tuple[str, int], tuple[bool, list[str] | None]]:
    llvm_definition_dir = foundry.llvm_library if use_booster else None

    def create_server() -> KoreServer:
        return kore_server(
            definition_dir=foundry.kevm.definition_dir,
            llvm_definition_dir=llvm_definition_dir,
            module_name=foundry.kevm.main_module,
            command=kore_rpc_command,
            bug_report=bug_report,
            smt_timeout=smt_timeout,
            smt_retry_limit=smt_retry_limit,
        )

    def init_and_run_proof(test: FoundryTest) -> tuple[bool, list[str] | None]:
        start_server = port is None

        with legacy_explore(
            foundry.kevm,
            kcfg_semantics=KEVMSemantics(auto_abstract_gas=auto_abstract_gas),
            id=test.id,
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
                test,
                kcfg_explore,
                simplify_init=simplify_init,
                bmc_depth=bmc_depth,
                run_constructor=run_constructor,
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

    _apr_proofs: list[tuple[bool, list[str] | None]]
    if workers > 1:
        with ProcessPool(ncpus=workers) as process_pool:
            _apr_proofs = process_pool.map(init_and_run_proof, tests)
    else:
        _apr_proofs = []
        for test in tests:
            _apr_proofs.append(init_and_run_proof(test))

    unparsed_tests = [test.unparsed for test in tests]
    apr_proofs = dict(zip(unparsed_tests, _apr_proofs, strict=True))
    return apr_proofs


def _contract_to_apr_proof(
    foundry: Foundry,
    contract: Contract,
    save_directory: Path,
    kcfg_explore: KCFGExplore,
    test_id: str,
    reinit: bool = False,
    simplify_init: bool = True,
    bmc_depth: int | None = None,
) -> APRProof:
    if contract.constructor is None:
        raise ValueError(
            f'Constructor proof cannot be generated for contract: {contract.name}, because it has no constructor.'
        )

    if len(contract.constructor.arg_names) > 0:
        raise ValueError(
            f'Proof cannot be generated for contract: {contract.name}. Constructors with arguments are not supported.'
        )

    apr_proof: APRProof

    if Proof.proof_data_exists(test_id, save_directory):
        apr_proof = foundry.get_apr_proof(test_id)
    else:
        _LOGGER.info(f'Initializing KCFG for test: {test_id}')

        empty_config = foundry.kevm.definition.empty_config(GENERATED_TOP_CELL)
        kcfg, init_node_id, target_node_id = _contract_to_cfg(
            empty_config,
            contract,
            save_directory,
            foundry=foundry,
        )

        _LOGGER.info(f'Expanding macros in initial state for test: {test_id}')
        init_term = kcfg.node(init_node_id).cterm.kast
        init_term = KDefinition__expand_macros(foundry.kevm.definition, init_term)
        init_cterm = CTerm.from_kast(init_term)
        _LOGGER.info(f'Computing definedness constraint for test: {test_id}')
        init_cterm = kcfg_explore.cterm_assume_defined(init_cterm)
        _LOGGER.info(f'Computing definedness constraint for test: {test_id} done')
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
                test_id, kcfg, [], init_node_id, target_node_id, {}, bmc_depth, proof_dir=save_directory
            )
        else:
            apr_proof = APRProof(test_id, kcfg, [], init_node_id, target_node_id, {}, proof_dir=save_directory)

    apr_proof.write_proof_data()
    return apr_proof


def method_to_apr_proof(
    foundry: Foundry,
    test: FoundryTest,
    kcfg_explore: KCFGExplore,
    simplify_init: bool = True,
    bmc_depth: int | None = None,
    run_constructor: bool = False,
) -> APRProof | APRBMCProof:
    if Proof.proof_data_exists(test.id, foundry.proofs_dir):
        apr_proof = foundry.get_apr_proof(test.id)
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

    kcfg, init_node_id, target_node_id = method_to_initialized_cfg(
        foundry,
        test,
        kcfg_explore,
        setup_proof=setup_proof,
        simplify_init=simplify_init,
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

    return apr_proof


def _contract_to_cfg(
    empty_config: KInner,
    contract: Contract,
    proof_dir: Path,
    foundry: Foundry,
    init_proof: str | None = None,
) -> tuple[KCFG, int, int]:
    program = KEVM.init_bytecode(KApply(f'contract_{contract.name}'))

    init_cterm = _init_cterm(empty_config, contract.name, program)

    cfg = KCFG()
    init_node = cfg.create_node(init_cterm)
    init_node_id = init_node.id

    final_cterm = _final_cterm(empty_config, contract.name, failing=False)
    target_node = cfg.create_node(final_cterm)

    return cfg, init_node_id, target_node.id


def _load_setup_proof(foundry: Foundry, contract: Contract) -> APRProof:
    latest_version = foundry.latest_proof_version(f'{contract.name}.setUp()')
    setup_digest = f'{contract.name}.setUp():{latest_version}'
    apr_proof = APRProof.read_proof_data(foundry.proofs_dir, setup_digest)
    return apr_proof


def _load_constructor_proof(foundry: Foundry, contract: Contract) -> APRProof:
    latest_version = foundry.latest_proof_version(f'{contract.name}.init')
    setup_digest = f'{contract.name}.init:{latest_version}'
    apr_proof = APRProof.read_proof_data(foundry.proofs_dir, setup_digest)
    return apr_proof


def method_to_initialized_cfg(
    foundry: Foundry,
    test: FoundryTest,
    kcfg_explore: KCFGExplore,
    *,
    setup_proof: APRProof | None = None,
    simplify_init: bool = True,
) -> tuple[KCFG, int, int]:
    _LOGGER.info(f'Initializing KCFG for test: {test.id}')

    empty_config = foundry.kevm.definition.empty_config(GENERATED_TOP_CELL)
    kcfg, new_node_ids, init_node_id, target_node_id = _method_to_cfg(
        empty_config,
        test.contract,
        test.method,
        setup_proof,
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

    if simplify_init:
        _LOGGER.info(f'Simplifying KCFG for test: {test.name}')
        kcfg_explore.simplify(kcfg, {})

    return kcfg, init_node_id, target_node_id


def _method_to_cfg(
    empty_config: KInner,
    contract: Contract,
    method: Contract.Method | Contract.Constructor,
    setup_proof: APRProof | None,
) -> tuple[KCFG, list[int], int, int]:
    calldata = None
    callvalue = None

    if isinstance(method, Contract.Constructor):
        program = KEVM.init_bytecode(KApply(f'contract_{contract.name}'))
        use_init_code = True

    elif isinstance(method, Contract.Method):
        calldata = method.calldata_cell(contract)
        callvalue = method.callvalue_cell
        program = KEVM.bin_runtime(KApply(f'contract_{contract.name}'))
        use_init_code = False

    init_cterm = _init_cterm(
        empty_config,
        contract.name,
        program=program,
        calldata=calldata,
        callvalue=callvalue,
    )
    new_node_ids = []

    if setup_proof:
        init_node_id = setup_proof.kcfg.node(setup_proof.init).id

        cfg = setup_proof.kcfg
        final_states = [cover.source for cover in cfg.covers(target_id=setup_proof.target)]
        cfg.remove_node(setup_proof.target)
        if len(setup_proof.pending) > 0:
            raise RuntimeError(
                f'Initial state proof {setup_proof.id} for {contract.name}.{method.signature} still has pending branches.'
            )
        if len(final_states) < 1:
            _LOGGER.warning(
                f'Initial state proof {setup_proof.id} for {contract.name}.{method.signature} has no passing branches to build on. Method will not be executed.'
            )
        for final_node in final_states:
            new_accounts_cell = final_node.cterm.cell('ACCOUNTS_CELL')
            new_accounts = [CTerm(account, []) for account in flatten_label('_AccountCellMap_', new_accounts_cell)]
            new_accounts_map = {account.cell('ACCTID_CELL'): account for account in new_accounts}
            test_contract_account = new_accounts_map[Foundry.address_TEST_CONTRACT()]

            new_accounts_map[Foundry.address_TEST_CONTRACT()] = CTerm(
                set_cell(
                    test_contract_account.config, 'CODE_CELL', KEVM.bin_runtime(KApply(f'contract_{contract.name}'))
                ),
                [],
            )

            new_accounts_cell = KEVM.accounts([account.config for account in new_accounts_map.values()])

            new_init_cterm = CTerm(set_cell(init_cterm.config, 'ACCOUNTS_CELL', new_accounts_cell), [])
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
        empty_config, contract.name, failing=failing, is_test=is_test, use_init_code=use_init_code
    )
    target_node = cfg.create_node(final_cterm)

    return cfg, new_node_ids, init_node_id, target_node.id


def _init_cterm(
    empty_config: KInner,
    contract_name: str,
    program: KInner,
    *,
    setup_cterm: CTerm | None = None,
    calldata: KInner | None = None,
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


def _get_final_accounts_cell(
    setup_cterm: CTerm, overwrite_code_cell: KInner | None = None
) -> tuple[KInner, Iterable[KInner]]:
    acct_cell = setup_cterm.cell('ACCOUNTS_CELL')

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
    acct_cons = constraints_for(fvars, setup_cterm.constraints)
    return (acct_cell, acct_cons)
