from __future__ import annotations

import json
import logging
import sys
from argparse import ArgumentParser
from typing import TYPE_CHECKING

from kevm_pyk import kdist
from kevm_pyk.cli import node_id_like
from kevm_pyk.utils import arg_pair_of
from pyk.cli.utils import file_path
from pyk.proof.tui import APRProofViewer

from . import VERSION
from .cli import KontrolCLIArgs
from .foundry import (
    Foundry,
    foundry_get_model,
    foundry_list,
    foundry_merge_nodes,
    foundry_node_printer,
    foundry_remove_node,
    foundry_section_edge,
    foundry_show,
    foundry_simplify_node,
    foundry_step_node,
    foundry_to_dot,
)
from .kompile import foundry_kompile
from .prove import foundry_prove
from .solc_to_k import solc_compile, solc_to_k

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Callable, Iterable
    from pathlib import Path
    from typing import Any, Final, TypeVar

    from pyk.cterm import CTerm
    from pyk.kcfg.kcfg import NodeIdLike
    from pyk.kcfg.tui import KCFGElem
    from pyk.utils import BugReport

    T = TypeVar('T')

_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


def _ignore_arg(args: dict[str, Any], arg: str, cli_option: str) -> None:
    if arg in args:
        if args[arg] is not None:
            _LOGGER.warning(f'Ignoring command-line option: {cli_option}')
        args.pop(arg)


def main() -> None:
    sys.setrecursionlimit(15000000)
    parser = _create_argument_parser()
    args = parser.parse_args()
    logging.basicConfig(level=_loglevel(args), format=_LOG_FORMAT)

    executor_name = 'exec_' + args.command.lower().replace('-', '_')
    if executor_name not in globals():
        raise AssertionError(f'Unimplemented command: {args.command}')

    execute = globals()[executor_name]
    execute(**vars(args))


# Command implementation


def exec_version(**kwargs: Any) -> None:
    print(f'Kontrol version: {VERSION}')


def exec_compile(contract_file: Path, **kwargs: Any) -> None:
    res = solc_compile(contract_file)
    print(json.dumps(res))


def exec_solc_to_k(
    contract_file: Path,
    contract_name: str,
    main_module: str | None,
    requires: list[str],
    imports: list[str],
    target: str | None = None,
    **kwargs: Any,
) -> None:
    if target is None:
        target = 'haskell'

    k_text = solc_to_k(
        definition_dir=kdist.get(target),
        contract_file=contract_file,
        contract_name=contract_name,
        main_module=main_module,
        requires=requires,
        imports=imports,
    )
    print(k_text)


def exec_build(
    foundry_root: Path,
    includes: Iterable[str] = (),
    regen: bool = False,
    rekompile: bool = False,
    requires: Iterable[str] = (),
    imports: Iterable[str] = (),
    ccopts: Iterable[str] = (),
    llvm_kompile: bool = True,
    debug: bool = False,
    llvm_library: bool = False,
    verbose: bool = False,
    **kwargs: Any,
) -> None:
    _ignore_arg(kwargs, 'main_module', f'--main-module {kwargs["main_module"]}')
    _ignore_arg(kwargs, 'syntax_module', f'--syntax-module {kwargs["syntax_module"]}')
    _ignore_arg(kwargs, 'spec_module', f'--spec-module {kwargs["spec_module"]}')
    _ignore_arg(kwargs, 'o0', '-O0')
    _ignore_arg(kwargs, 'o1', '-O1')
    _ignore_arg(kwargs, 'o2', '-O2')
    _ignore_arg(kwargs, 'o3', '-O3')
    foundry_kompile(
        foundry_root=foundry_root,
        includes=includes,
        regen=regen,
        rekompile=rekompile,
        requires=requires,
        imports=imports,
        ccopts=ccopts,
        llvm_kompile=llvm_kompile,
        debug=debug,
        verbose=verbose,
    )


def exec_prove(
    foundry_root: Path,
    max_depth: int = 1000,
    max_iterations: int | None = None,
    reinit: bool = False,
    tests: Iterable[tuple[str, int | None]] = (),
    workers: int = 1,
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
    run_constructor: bool = False,
    **kwargs: Any,
) -> None:
    _ignore_arg(kwargs, 'main_module', f'--main-module: {kwargs["main_module"]}')
    _ignore_arg(kwargs, 'syntax_module', f'--syntax-module: {kwargs["syntax_module"]}')
    _ignore_arg(kwargs, 'definition_dir', f'--definition: {kwargs["definition_dir"]}')
    _ignore_arg(kwargs, 'spec_module', f'--spec-module: {kwargs["spec_module"]}')

    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    if isinstance(kore_rpc_command, str):
        kore_rpc_command = kore_rpc_command.split()

    results = foundry_prove(
        foundry_root=foundry_root,
        max_depth=max_depth,
        max_iterations=max_iterations,
        reinit=reinit,
        tests=tests,
        workers=workers,
        break_every_step=break_every_step,
        break_on_jumpi=break_on_jumpi,
        break_on_calls=break_on_calls,
        bmc_depth=bmc_depth,
        bug_report=bug_report,
        kore_rpc_command=kore_rpc_command,
        use_booster=use_booster,
        counterexample_info=counterexample_info,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        trace_rewrites=trace_rewrites,
        auto_abstract_gas=auto_abstract_gas,
        run_constructor=run_constructor,
    )
    failed = 0
    for pid, r in results.items():
        passed, failure_log = r
        if passed:
            print(f'PROOF PASSED: {pid}')
        else:
            failed += 1
            print(f'PROOF FAILED: {pid}')
            if failure_info and failure_log is not None:
                failure_log += Foundry.help_info()
                for line in failure_log:
                    print(line)

    sys.exit(failed)


def exec_show(
    foundry_root: Path,
    test: str,
    version: int | None,
    nodes: Iterable[NodeIdLike] = (),
    node_deltas: Iterable[tuple[NodeIdLike, NodeIdLike]] = (),
    to_module: bool = False,
    minimize: bool = True,
    sort_collections: bool = False,
    omit_unstable_output: bool = False,
    pending: bool = False,
    failing: bool = False,
    failure_info: bool = False,
    counterexample_info: bool = False,
    **kwargs: Any,
) -> None:
    output = foundry_show(
        foundry_root=foundry_root,
        test=test,
        version=version,
        nodes=nodes,
        node_deltas=node_deltas,
        to_module=to_module,
        minimize=minimize,
        omit_unstable_output=omit_unstable_output,
        sort_collections=sort_collections,
        pending=pending,
        failing=failing,
        failure_info=failure_info,
        counterexample_info=counterexample_info,
    )
    print(output)


def exec_to_dot(foundry_root: Path, test: str, version: int | None, **kwargs: Any) -> None:
    foundry_to_dot(foundry_root=foundry_root, test=test, version=version)


def exec_list(foundry_root: Path, **kwargs: Any) -> None:
    stats = foundry_list(foundry_root=foundry_root)
    print('\n'.join(stats))


def exec_view_kcfg(foundry_root: Path, test: str, version: int | None, **kwargs: Any) -> None:
    foundry = Foundry(foundry_root)
    test_id = foundry.get_test_id(test, version)
    contract_name, _ = test_id.split('.')
    proof = foundry.get_apr_proof(test_id)

    def _short_info(cterm: CTerm) -> Iterable[str]:
        return foundry.short_info_for_contract(contract_name, cterm)

    def _custom_view(elem: KCFGElem) -> Iterable[str]:
        return foundry.custom_view(contract_name, elem)

    node_printer = foundry_node_printer(foundry, contract_name, proof)
    viewer = APRProofViewer(proof, foundry.kevm, node_printer=node_printer, custom_view=_custom_view)
    viewer.run()


def exec_remove_node(foundry_root: Path, test: str, node: NodeIdLike, version: int | None, **kwargs: Any) -> None:
    foundry_remove_node(foundry_root=foundry_root, test=test, version=version, node=node)


def exec_simplify_node(
    foundry_root: Path,
    test: str,
    version: int | None,
    node: NodeIdLike,
    replace: bool = False,
    minimize: bool = True,
    sort_collections: bool = False,
    bug_report: BugReport | None = None,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    trace_rewrites: bool = False,
    **kwargs: Any,
) -> None:
    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    pretty_term = foundry_simplify_node(
        foundry_root=foundry_root,
        test=test,
        version=version,
        node=node,
        replace=replace,
        minimize=minimize,
        sort_collections=sort_collections,
        bug_report=bug_report,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        trace_rewrites=trace_rewrites,
    )
    print(f'Simplified:\n{pretty_term}')


def exec_step_node(
    foundry_root: Path,
    test: str,
    version: int | None,
    node: NodeIdLike,
    repeat: int = 1,
    depth: int = 1,
    bug_report: BugReport | None = None,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    trace_rewrites: bool = False,
    **kwargs: Any,
) -> None:
    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    foundry_step_node(
        foundry_root=foundry_root,
        test=test,
        version=version,
        node=node,
        repeat=repeat,
        depth=depth,
        bug_report=bug_report,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        trace_rewrites=trace_rewrites,
    )


def exec_merge_nodes(
    foundry_root: Path,
    test: str,
    version: int | None,
    nodes: Iterable[NodeIdLike],
    **kwargs: Any,
) -> None:
    foundry_merge_nodes(foundry_root=foundry_root, node_ids=nodes, test=test, version=version)


def exec_section_edge(
    foundry_root: Path,
    test: str,
    version: int | None,
    edge: tuple[str, str],
    sections: int = 2,
    replace: bool = False,
    bug_report: BugReport | None = None,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    trace_rewrites: bool = False,
    **kwargs: Any,
) -> None:
    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    foundry_section_edge(
        foundry_root=foundry_root,
        test=test,
        version=version,
        edge=edge,
        sections=sections,
        replace=replace,
        bug_report=bug_report,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        trace_rewrites=trace_rewrites,
    )


def exec_get_model(
    foundry_root: Path,
    test: str,
    version: int | None,
    nodes: Iterable[NodeIdLike] = (),
    pending: bool = False,
    failing: bool = False,
    **kwargs: Any,
) -> None:
    output = foundry_get_model(
        foundry_root=foundry_root,
        test=test,
        version=version,
        nodes=nodes,
        pending=pending,
        failing=failing,
    )
    print(output)


# Helpers


def _create_argument_parser() -> ArgumentParser:
    def list_of(elem_type: Callable[[str], T], delim: str = ';') -> Callable[[str], list[T]]:
        def parse(s: str) -> list[T]:
            return [elem_type(elem) for elem in s.split(delim)]

        return parse

    kontrol_cli_args = KontrolCLIArgs()
    parser = ArgumentParser(prog='kontrol')

    command_parser = parser.add_subparsers(dest='command', required=True)

    command_parser.add_parser('version', help='Print out version of Kontrol command.')

    solc_args = command_parser.add_parser('compile', help='Generate combined JSON with solc compilation results.')
    solc_args.add_argument('contract_file', type=file_path, help='Path to contract file.')

    solc_to_k_args = command_parser.add_parser(
        'solc-to-k',
        help='Output helper K definition for given JSON output from solc compiler.',
        parents=[
            kontrol_cli_args.logging_args,
            kontrol_cli_args.target_args,
            kontrol_cli_args.k_args,
            kontrol_cli_args.k_gen_args,
        ],
    )
    solc_to_k_args.add_argument('contract_file', type=file_path, help='Path to contract file.')
    solc_to_k_args.add_argument('contract_name', type=str, help='Name of contract to generate K helpers for.')

    def _parse_test_version_tuple(value: str) -> tuple[str, int | None]:
        if ':' in value:
            test, version = value.split(':')
            return (test, int(version))
        else:
            return (value, None)

    build = command_parser.add_parser(
        'build',
        help='Kompile K definition corresponding to given output directory.',
        parents=[
            kontrol_cli_args.logging_args,
            kontrol_cli_args.k_args,
            kontrol_cli_args.k_gen_args,
            kontrol_cli_args.kompile_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    build.add_argument(
        '--regen',
        dest='regen',
        default=False,
        action='store_true',
        help='Regenerate foundry.k even if it already exists.',
    )
    build.add_argument(
        '--rekompile',
        dest='rekompile',
        default=False,
        action='store_true',
        help='Rekompile foundry.k even if kompiled definition already exists.',
    )

    prove_args = command_parser.add_parser(
        'prove',
        help='Run Foundry Proof.',
        parents=[
            kontrol_cli_args.logging_args,
            kontrol_cli_args.parallel_args,
            kontrol_cli_args.k_args,
            kontrol_cli_args.kprove_args,
            kontrol_cli_args.smt_args,
            kontrol_cli_args.rpc_args,
            kontrol_cli_args.bug_report_args,
            kontrol_cli_args.explore_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    prove_args.add_argument(
        '--test',
        type=_parse_test_version_tuple,
        dest='tests',
        default=[],
        action='append',
        help=(
            "Specify the contract function to test in the format 'ContractName.FunctionName'. If a function is "
            "overloaded, you should specify the full signature, e.g., 'ERC20Test.testTransfer(address,uint256)'. This "
            'option can be used multiple times to test multiple functions.'
        ),
    )
    prove_args.add_argument(
        '--reinit',
        dest='reinit',
        default=False,
        action='store_true',
        help='Reinitialize CFGs even if they already exist.',
    )
    prove_args.add_argument(
        '--bmc-depth',
        dest='bmc_depth',
        default=None,
        type=int,
        help='Enables bounded model checking. Specifies the maximum depth to unroll all loops to.',
    )
    prove_args.add_argument(
        '--use-booster',
        dest='use_booster',
        default=False,
        action='store_true',
        help='Use the booster RPC server instead of kore-rpc.',
    )
    prove_args.add_argument(
        '--run-constructor',
        dest='run_constructor',
        default=False,
        action='store_true',
        help='Include the contract constructor in the test execution.',
    )

    show_args = command_parser.add_parser(
        'show',
        help='Display a given Foundry CFG.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.k_args,
            kontrol_cli_args.kcfg_show_args,
            kontrol_cli_args.display_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    show_args.add_argument(
        '--omit-unstable-output',
        dest='omit_unstable_output',
        default=False,
        action='store_true',
        help='Strip output that is likely to change without the contract logic changing',
    )

    command_parser.add_parser(
        'to-dot',
        help='Dump the given CFG for the test as DOT for visualization.',
        parents=[kontrol_cli_args.foundry_test_args, kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args],
    )

    command_parser.add_parser(
        'list',
        help='List information about CFGs on disk',
        parents=[kontrol_cli_args.logging_args, kontrol_cli_args.k_args, kontrol_cli_args.foundry_args],
    )

    command_parser.add_parser(
        'view-kcfg',
        help='Display tree view of CFG',
        parents=[kontrol_cli_args.foundry_test_args, kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args],
    )

    remove_node = command_parser.add_parser(
        'remove-node',
        help='Remove a node and its successors.',
        parents=[kontrol_cli_args.foundry_test_args, kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args],
    )
    remove_node.add_argument('node', type=node_id_like, help='Node to remove CFG subgraph from.')

    simplify_node = command_parser.add_parser(
        'simplify-node',
        help='Simplify a given node, and potentially replace it.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.smt_args,
            kontrol_cli_args.rpc_args,
            kontrol_cli_args.bug_report_args,
            kontrol_cli_args.display_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    simplify_node.add_argument('node', type=node_id_like, help='Node to simplify in CFG.')
    simplify_node.add_argument(
        '--replace', default=False, help='Replace the original node with the simplified variant in the graph.'
    )

    step_node = command_parser.add_parser(
        'step-node',
        help='Step from a given node, adding it to the CFG.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.rpc_args,
            kontrol_cli_args.bug_report_args,
            kontrol_cli_args.smt_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    step_node.add_argument('node', type=node_id_like, help='Node to step from in CFG.')
    step_node.add_argument(
        '--repeat', type=int, default=1, help='How many node expansions to do from the given start node (>= 1).'
    )
    step_node.add_argument('--depth', type=int, default=1, help='How many steps to take from initial node on edge.')
    merge_node = command_parser.add_parser(
        'merge-nodes',
        help='Merge multiple nodes into one branch.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    merge_node.add_argument(
        '--node',
        type=node_id_like,
        dest='nodes',
        default=[],
        action='append',
        help='One node to be merged.',
    )

    section_edge = command_parser.add_parser(
        'section-edge',
        help='Given an edge in the graph, cut it into sections to get intermediate nodes.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.rpc_args,
            kontrol_cli_args.bug_report_args,
            kontrol_cli_args.smt_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    section_edge.add_argument('edge', type=arg_pair_of(str, str), help='Edge to section in CFG.')
    section_edge.add_argument('--sections', type=int, default=2, help='Number of sections to make from edge (>= 2).')

    get_model = command_parser.add_parser(
        'get-model',
        help='Display a model for a given node.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.rpc_args,
            kontrol_cli_args.smt_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    get_model.add_argument(
        '--node',
        type=node_id_like,
        dest='nodes',
        default=[],
        action='append',
        help='List of nodes to display the models of.',
    )
    get_model.add_argument(
        '--pending', dest='pending', default=False, action='store_true', help='Also display models of pending nodes'
    )
    get_model.add_argument(
        '--failing', dest='failing', default=False, action='store_true', help='Also display models of failing nodes'
    )

    return parser


def _loglevel(args: Namespace) -> int:
    if hasattr(args, 'debug') and args.debug:
        return logging.DEBUG

    if hasattr(args, 'verbose') and args.verbose:
        return logging.INFO

    return logging.WARNING


if __name__ == '__main__':
    main()
