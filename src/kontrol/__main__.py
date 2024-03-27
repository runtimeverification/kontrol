from __future__ import annotations

import json
import logging
import sys
from argparse import ArgumentParser
from typing import TYPE_CHECKING

import pyk
from kevm_pyk.cli import node_id_like
from kevm_pyk.kompile import KompileTarget
from kevm_pyk.utils import arg_pair_of
from pyk.cli.utils import file_path
from pyk.cterm.symbolic import CTermSMTError
from pyk.kbuild.utils import KVersion, k_version
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.proof.tui import APRProofViewer
from pyk.utils import ensure_dir_path

from . import VERSION
from .cli import KontrolCLIArgs
from .foundry import (
    Foundry,
    foundry_get_model,
    foundry_list,
    foundry_merge_nodes,
    foundry_node_printer,
    foundry_refute_node,
    foundry_remove_node,
    foundry_section_edge,
    foundry_show,
    foundry_simplify_node,
    foundry_split_node,
    foundry_state_diff,
    foundry_step_node,
    foundry_to_dot,
    foundry_unrefute_node,
    read_deployment_state,
)
from .hevm import Hevm
from .kompile import foundry_kompile
from .options import ProveOptions, RPCOptions
from .prove import foundry_prove, parse_test_version_tuple
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


def _load_foundry(foundry_root: Path, bug_report: BugReport | None = None) -> Foundry:
    try:
        foundry = Foundry(foundry_root=foundry_root, bug_report=bug_report)
    except FileNotFoundError:
        print(
            f'File foundry.toml not found in: {str(foundry_root)!r}. Are you running kontrol in a Foundry project?',
            file=sys.stderr,
        )
        sys.exit(1)
    return foundry


def main() -> None:
    sys.setrecursionlimit(15000000)
    parser = _create_argument_parser()
    args = parser.parse_args()
    logging.basicConfig(level=_loglevel(args), format=_LOG_FORMAT)

    _check_k_version()

    executor_name = 'exec_' + args.command.lower().replace('-', '_')
    if executor_name not in globals():
        raise AssertionError(f'Unimplemented command: {args.command}')

    execute = globals()[executor_name]
    execute(**vars(args))


def _check_k_version() -> None:
    expected_k_version = KVersion.parse(f'v{pyk.K_VERSION}')
    actual_k_version = k_version()

    if not _compare_versions(expected_k_version, actual_k_version):
        _LOGGER.warning(
            f'K version {expected_k_version.text} was expected but K version {actual_k_version.text} is being used.'
        )


def _compare_versions(ver1: KVersion, ver2: KVersion) -> bool:
    if ver1.major != ver2.major or ver1.minor != ver2.minor or ver1.patch != ver2.patch:
        return False

    if ver1.git == ver2.git:
        return True

    if ver1.git and ver2.git:
        return False

    git = ver1.git or ver2.git
    assert git  # git is not None for exactly one of ver1 and ver2
    return not git.ahead and not git.dirty


# Command implementation


def exec_load_state_diff(
    name: str,
    accesses_file: Path,
    contract_names: Path | None,
    output_dir_name: str | None,
    foundry_root: Path,
    license: str,
    comment_generated_file: str,
    condense_state_diff: bool = False,
    **kwargs: Any,
) -> None:
    foundry_state_diff(
        name,
        accesses_file,
        contract_names=contract_names,
        output_dir_name=output_dir_name,
        foundry=_load_foundry(foundry_root),
        license=license,
        comment_generated_file=comment_generated_file,
        condense_state_diff=condense_state_diff,
    )


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
    k_text = solc_to_k(
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
    target: KompileTarget | None = None,
    no_forge_build: bool = False,
    **kwargs: Any,
) -> None:
    _ignore_arg(kwargs, 'main_module', f'--main-module {kwargs["main_module"]}')
    _ignore_arg(kwargs, 'syntax_module', f'--syntax-module {kwargs["syntax_module"]}')
    _ignore_arg(kwargs, 'o0', '-O0')
    _ignore_arg(kwargs, 'o1', '-O1')
    _ignore_arg(kwargs, 'o2', '-O2')
    _ignore_arg(kwargs, 'o3', '-O3')
    if target is None:
        target = KompileTarget.HASKELL
    foundry_kompile(
        foundry=_load_foundry(foundry_root),
        includes=includes,
        regen=regen,
        rekompile=rekompile,
        requires=requires,
        imports=imports,
        ccopts=ccopts,
        llvm_kompile=llvm_kompile,
        debug=debug,
        verbose=verbose,
        target=target,
        no_forge_build=no_forge_build,
    )


def exec_prove(
    foundry_root: Path,
    max_depth: int = 1000,
    max_iterations: int | None = None,
    reinit: bool = False,
    tests: Iterable[tuple[str, int | None]] = (),
    include_summaries: Iterable[tuple[str, int | None]] = (),
    workers: int = 1,
    break_every_step: bool = False,
    break_on_jumpi: bool = False,
    break_on_calls: bool = False,
    break_on_storage: bool = False,
    break_on_basic_blocks: bool = False,
    break_on_cheatcodes: bool = False,
    bmc_depth: int | None = None,
    bug_report: BugReport | None = None,
    kore_rpc_command: str | Iterable[str] | None = None,
    use_booster: bool = True,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    smt_tactic: str | None = None,
    failure_info: bool = True,
    counterexample_info: bool = True,
    trace_rewrites: bool = False,
    auto_abstract_gas: bool = False,
    run_constructor: bool = False,
    fail_fast: bool = True,
    port: int | None = None,
    maude_port: int | None = None,
    use_gas: bool = False,
    deployment_state_path: Path | None = None,
    with_non_general_state: bool = False,
    xml_test_report: bool = False,
    cse: bool = False,
    hevm: bool = False,
    **kwargs: Any,
) -> None:
    _ignore_arg(kwargs, 'main_module', f'--main-module: {kwargs["main_module"]}')
    _ignore_arg(kwargs, 'syntax_module', f'--syntax-module: {kwargs["syntax_module"]}')
    _ignore_arg(kwargs, 'definition_dir', f'--definition: {kwargs["definition_dir"]}')

    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    if isinstance(kore_rpc_command, str):
        kore_rpc_command = kore_rpc_command.split()

    deployment_state_entries = read_deployment_state(deployment_state_path) if deployment_state_path else None

    prove_options = ProveOptions(
        auto_abstract_gas=auto_abstract_gas,
        reinit=reinit,
        bug_report=bug_report,
        bmc_depth=bmc_depth,
        max_depth=max_depth,
        break_every_step=break_every_step,
        break_on_jumpi=break_on_jumpi,
        break_on_calls=break_on_calls,
        break_on_storage=break_on_storage,
        break_on_basic_blocks=break_on_basic_blocks,
        break_on_cheatcodes=break_on_cheatcodes,
        workers=workers,
        counterexample_info=counterexample_info,
        max_iterations=max_iterations,
        run_constructor=run_constructor,
        fail_fast=fail_fast,
        use_gas=use_gas,
        deployment_state_entries=deployment_state_entries,
        active_symbolik=with_non_general_state,
        cse=cse,
        hevm=hevm,
    )

    rpc_options = RPCOptions(
        use_booster=use_booster,
        kore_rpc_command=kore_rpc_command,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        smt_tactic=smt_tactic,
        trace_rewrites=trace_rewrites,
        port=port,
        maude_port=maude_port,
    )

    try:
        results = foundry_prove(
            foundry=_load_foundry(foundry_root, bug_report),
            prove_options=prove_options,
            rpc_options=rpc_options,
            tests=tests,
            include_summaries=include_summaries,
            xml_test_report=xml_test_report,
        )
    except CTermSMTError as err:
        raise RuntimeError(
            f'SMT solver error; SMT timeout occured. SMT timeout parameter is currently set to {smt_timeout} ms, you may consider setting it with "--smt-timeout" command line argument. Related KAST pattern provided below:\n{err.message}'
        ) from err

    failed = 0
    for proof in results:
        _, test = proof.id.split('.')
        if not any(test.startswith(prefix) for prefix in ['test', 'check', 'prove']):
            signature, _ = test.split(':')
            _LOGGER.warning(
                f"{signature} is not prefixed with 'test', 'prove', or 'check', therefore, it is not reported as failing in the presence of reverts or assertion violations."
            )
        if proof.passed:
            print(f'PROOF PASSED: {proof.id}')
            print(f'time: {proof.formatted_exec_time()}')
        else:
            failed += 1
            print(f'PROOF FAILED: {proof.id}')
            print(f'time: {proof.formatted_exec_time()}')
            failure_log = None
            if isinstance(proof, APRProof) and isinstance(proof.failure_info, APRFailureInfo):
                failure_log = proof.failure_info
            if failure_info and failure_log is not None:
                log = failure_log.print() + (Foundry.help_info() if not hevm else Hevm.help_info(proof.id))
                for line in log:
                    print(line)
            refuted_nodes = list(proof.node_refutations.keys())
            if len(refuted_nodes) > 0:
                print(f'The proof cannot be completed while there are refuted nodes: {refuted_nodes}.')
                print('Either unrefute the nodes or discharge the corresponding refutation subproofs.')

    sys.exit(failed)


def exec_show(
    foundry_root: Path,
    test: str,
    version: int | None,
    nodes: Iterable[NodeIdLike] = (),
    node_deltas: Iterable[tuple[NodeIdLike, NodeIdLike]] = (),
    to_module: bool = False,
    to_kevm_claims: bool = False,
    kevm_claim_dir: Path | None = None,
    minimize: bool = True,
    sort_collections: bool = False,
    omit_unstable_output: bool = False,
    pending: bool = False,
    failing: bool = False,
    failure_info: bool = False,
    counterexample_info: bool = True,
    port: int | None = None,
    maude_port: int | None = None,
    **kwargs: Any,
) -> None:
    output = foundry_show(
        foundry=_load_foundry(foundry_root),
        test=test,
        version=version,
        nodes=nodes,
        node_deltas=node_deltas,
        to_module=to_module,
        to_kevm_claims=to_kevm_claims,
        kevm_claim_dir=kevm_claim_dir,
        minimize=minimize,
        omit_unstable_output=omit_unstable_output,
        sort_collections=sort_collections,
        pending=pending,
        failing=failing,
        failure_info=failure_info,
        counterexample_info=counterexample_info,
        port=port,
        maude_port=maude_port,
    )
    print(output)


def exec_refute_node(foundry_root: Path, test: str, node: NodeIdLike, version: int | None, **kwargs: Any) -> None:
    foundry = _load_foundry(foundry_root)
    refutation = foundry_refute_node(foundry=foundry, test=test, node=node, version=version)

    if refutation:
        claim, _ = refutation.to_claim('refuted-' + str(node))
        print('\nClaim for the refutation:\n')
        print(foundry.kevm.pretty_print(claim))
        print('\n')
    else:
        raise ValueError(f'Unable to refute node for test {test}: {node}')


def exec_unrefute_node(foundry_root: Path, test: str, node: NodeIdLike, version: int | None, **kwargs: Any) -> None:
    foundry_unrefute_node(foundry=_load_foundry(foundry_root), test=test, node=node, version=version)


def exec_split_node(
    foundry_root: Path, test: str, node: NodeIdLike, branch_condition: str, version: int | None, **kwargs: Any
) -> None:
    node_ids = foundry_split_node(
        foundry=_load_foundry(foundry_root), test=test, node=node, branch_condition=branch_condition, version=version
    )

    print(f'Node {node} has been split into {node_ids} on condition {branch_condition}.')


def exec_to_dot(foundry_root: Path, test: str, version: int | None, **kwargs: Any) -> None:
    foundry_to_dot(foundry=_load_foundry(foundry_root), test=test, version=version)


def exec_list(foundry_root: Path, **kwargs: Any) -> None:
    stats = foundry_list(foundry=_load_foundry(foundry_root))
    print('\n'.join(stats))


def exec_view_kcfg(foundry_root: Path, test: str, version: int | None, **kwargs: Any) -> None:
    foundry = _load_foundry(foundry_root)
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
    foundry_remove_node(foundry=_load_foundry(foundry_root), test=test, version=version, node=node)


def exec_simplify_node(
    foundry_root: Path,
    test: str,
    version: int | None,
    node: NodeIdLike,
    replace: bool = False,
    minimize: bool = True,
    sort_collections: bool = False,
    bug_report: BugReport | None = None,
    kore_rpc_command: str | Iterable[str] | None = None,
    use_booster: bool = False,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    smt_tactic: str | None = None,
    trace_rewrites: bool = False,
    port: int | None = None,
    maude_port: int | None = None,
    **kwargs: Any,
) -> None:
    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    if isinstance(kore_rpc_command, str):
        kore_rpc_command = kore_rpc_command.split()

    rpc_options = RPCOptions(
        use_booster=use_booster,
        kore_rpc_command=kore_rpc_command,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        smt_tactic=smt_tactic,
        trace_rewrites=trace_rewrites,
        port=port,
        maude_port=maude_port,
    )

    pretty_term = foundry_simplify_node(
        foundry=_load_foundry(foundry_root, bug_report),
        test=test,
        version=version,
        node=node,
        rpc_options=rpc_options,
        replace=replace,
        minimize=minimize,
        sort_collections=sort_collections,
        bug_report=bug_report,
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
    kore_rpc_command: str | Iterable[str] | None = None,
    use_booster: bool = False,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    smt_tactic: str | None = None,
    trace_rewrites: bool = False,
    port: int | None = None,
    maude_port: int | None = None,
    **kwargs: Any,
) -> None:
    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    if isinstance(kore_rpc_command, str):
        kore_rpc_command = kore_rpc_command.split()

    rpc_options = RPCOptions(
        use_booster=use_booster,
        kore_rpc_command=kore_rpc_command,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        smt_tactic=smt_tactic,
        trace_rewrites=trace_rewrites,
        port=port,
        maude_port=maude_port,
    )

    foundry_step_node(
        foundry=_load_foundry(foundry_root, bug_report),
        test=test,
        version=version,
        node=node,
        rpc_options=rpc_options,
        repeat=repeat,
        depth=depth,
        bug_report=bug_report,
    )


def exec_merge_nodes(
    foundry_root: Path,
    test: str,
    version: int | None,
    nodes: Iterable[NodeIdLike],
    **kwargs: Any,
) -> None:
    foundry_merge_nodes(foundry=_load_foundry(foundry_root), node_ids=nodes, test=test, version=version)


def exec_section_edge(
    foundry_root: Path,
    test: str,
    version: int | None,
    edge: tuple[str, str],
    sections: int = 2,
    replace: bool = False,
    bug_report: BugReport | None = None,
    kore_rpc_command: str | Iterable[str] | None = None,
    use_booster: bool = False,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    smt_tactic: str | None = None,
    trace_rewrites: bool = False,
    port: int | None = None,
    maude_port: int | None = None,
    **kwargs: Any,
) -> None:
    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    if isinstance(kore_rpc_command, str):
        kore_rpc_command = kore_rpc_command.split()

    rpc_options = RPCOptions(
        use_booster=use_booster,
        kore_rpc_command=kore_rpc_command,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        smt_tactic=smt_tactic,
        trace_rewrites=trace_rewrites,
        port=port,
        maude_port=maude_port,
    )

    foundry_section_edge(
        foundry=_load_foundry(foundry_root, bug_report),
        test=test,
        version=version,
        rpc_options=rpc_options,
        edge=edge,
        sections=sections,
        replace=replace,
        bug_report=bug_report,
    )


def exec_get_model(
    foundry_root: Path,
    test: str,
    version: int | None,
    nodes: Iterable[NodeIdLike] = (),
    pending: bool = False,
    failing: bool = False,
    bug_report: BugReport | None = None,
    kore_rpc_command: str | Iterable[str] | None = None,
    use_booster: bool = False,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    smt_tactic: str | None = None,
    trace_rewrites: bool = False,
    port: int | None = None,
    maude_port: int | None = None,
    **kwargs: Any,
) -> None:
    if smt_timeout is None:
        smt_timeout = 300
    if smt_retry_limit is None:
        smt_retry_limit = 10

    if isinstance(kore_rpc_command, str):
        kore_rpc_command = kore_rpc_command.split()

    rpc_options = RPCOptions(
        use_booster=use_booster,
        kore_rpc_command=kore_rpc_command,
        smt_timeout=smt_timeout,
        smt_retry_limit=smt_retry_limit,
        smt_tactic=smt_tactic,
        trace_rewrites=trace_rewrites,
        port=port,
        maude_port=maude_port,
    )
    output = foundry_get_model(
        foundry=_load_foundry(foundry_root),
        test=test,
        version=version,
        nodes=nodes,
        rpc_options=rpc_options,
        pending=pending,
        failing=failing,
        bug_report=bug_report,
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
            kontrol_cli_args.k_args,
            kontrol_cli_args.k_gen_args,
        ],
    )
    solc_to_k_args.add_argument('contract_file', type=file_path, help='Path to contract file.')
    solc_to_k_args.add_argument('contract_name', type=str, help='Name of contract to generate K helpers for.')

    build = command_parser.add_parser(
        'build',
        help='Kompile K definition corresponding to given output directory.',
        parents=[
            kontrol_cli_args.logging_args,
            kontrol_cli_args.k_args,
            kontrol_cli_args.k_gen_args,
            kontrol_cli_args.kompile_args,
            kontrol_cli_args.foundry_args,
            kontrol_cli_args.kompile_target_args,
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
    build.add_argument(
        '--no-forge-build',
        dest='no_forge_build',
        default=False,
        action='store_true',
        help="Do not call 'forge build' during kompilation.",
    )

    state_diff_args = command_parser.add_parser(
        'load-state-diff',
        help='Generate a state diff summary from an account access dict',
        parents=[
            kontrol_cli_args.foundry_args,
        ],
    )
    state_diff_args.add_argument('name', type=str, help='Generated contract name')
    state_diff_args.add_argument('accesses_file', type=file_path, help='Path to accesses file')
    state_diff_args.add_argument(
        '--contract-names',
        dest='contract_names',
        default=None,
        type=file_path,
        help='Path to JSON containing deployment addresses and its respective contract names',
    )
    state_diff_args.add_argument(
        '--condense-state-diff',
        dest='condense_state_diff',
        default=False,
        type=bool,
        help='Deploy state diff as a single file',
    )
    state_diff_args.add_argument(
        '--output-dir',
        dest='output_dir_name',
        default=None,
        type=str,
        help='Path to write state diff .sol files, relative to foundry root',
    )
    state_diff_args.add_argument(
        '--comment-generated-files',
        dest='comment_generated_file',
        default='// This file was autogenerated by running `kontrol load-state-diff`. Do not edit this file manually.\n',
        type=str,
        help='Comment to write at the top of the auto generated state diff files',
    )
    state_diff_args.add_argument(
        '--license',
        dest='license',
        default='UNLICENSED',
        type=str,
        help='License for the auto generated contracts',
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
        '--match-test',
        type=parse_test_version_tuple,
        dest='tests',
        default=[],
        action='append',
        help=(
            'Specify contract function(s) to test using a regular expression. This will match functions'
            " based on their full signature,  e.g., 'ERC20Test.testTransfer(address,uint256)'. This option"
            ' can be used multiple times to add more functions to test.'
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
        '--run-constructor',
        dest='run_constructor',
        default=False,
        action='store_true',
        help='Include the contract constructor in the test execution.',
    )
    prove_args.add_argument(
        '--use-gas', dest='use_gas', default=False, action='store_true', help='Enables gas computation in KEVM.'
    )
    prove_args.add_argument(
        '--break-on-cheatcodes',
        dest='break_on_cheatcodes',
        default=False,
        action='store_true',
        help='Break on all Foundry rules.',
    )
    prove_args.add_argument(
        '--init-node-from',
        dest='deployment_state_path',
        default=None,
        type=file_path,
        help='Path to JSON file containing the deployment state of the deployment process used for the project.',
    )
    prove_args.add_argument(
        '--include-summary',
        type=parse_test_version_tuple,
        dest='include_summaries',
        default=[],
        action='append',
        help='Specify a summary to include as a lemma.',
    )
    prove_args.add_argument(
        '--with-non-general-state',
        dest='with_non_general_state',
        default=False,
        action='store_true',
        help='Flag used by Simbolik to initialise the state of a non test function as if it was a test function.',
    )
    prove_args.add_argument(
        '--xml-test-report',
        dest='xml_test_report',
        default=False,
        action='store_true',
        help='Generate a JUnit XML report',
    )
    prove_args.add_argument(
        '--cse', dest='cse', default=False, action='store_true', help='Use Compositional Symbolic Execution'
    )
    prove_args.add_argument(
        '--hevm',
        dest='hevm',
        default=False,
        action='store_true',
        help='Use hevm success predicate instead of foundry to determine if a test is passing',
    )

    show_args = command_parser.add_parser(
        'show',
        help='Print the CFG for a given proof.',
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
    show_args.add_argument(
        '--to-kevm-claims',
        dest='to_kevm_claims',
        default=False,
        action='store_true',
        help='Generate a K module which can be run directly as KEVM claims for the given KCFG (best-effort).',
    )
    show_args.add_argument(
        '--kevm-claim-dir',
        dest='kevm_claim_dir',
        type=ensure_dir_path,
        help='Path to write KEVM claim files at.',
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
        help='Explore a given proof in the KCFG visualizer.',
        parents=[kontrol_cli_args.foundry_test_args, kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args],
    )

    remove_node = command_parser.add_parser(
        'remove-node',
        help='Remove a node and its successors.',
        parents=[kontrol_cli_args.foundry_test_args, kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args],
    )
    remove_node.add_argument('node', type=node_id_like, help='Node to remove CFG subgraph from.')

    refute_node = command_parser.add_parser(
        'refute-node',
        help='Refute a node and add its refutation as a subproof.',
        parents=[kontrol_cli_args.foundry_test_args, kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args],
    )
    refute_node.add_argument('node', type=node_id_like, help='Node to refute.')

    unrefute_node = command_parser.add_parser(
        'unrefute-node',
        help='Disable refutation of a node and remove corresponding refutation subproof.',
        parents=[kontrol_cli_args.foundry_test_args, kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args],
    )
    unrefute_node.add_argument('node', type=node_id_like, help='Node to unrefute.')

    split_node = command_parser.add_parser(
        'split-node',
        help='Split a node on a given branch condition.',
        parents=[kontrol_cli_args.foundry_test_args, kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args],
    )
    split_node.add_argument('node', type=node_id_like, help='Node to split.')
    split_node.add_argument('branch_condition', type=str, help='Branch condition written in K.')

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
            kontrol_cli_args.bug_report_args,
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
