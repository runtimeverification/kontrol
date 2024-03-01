from __future__ import annotations

import json
import logging
import sys
from typing import TYPE_CHECKING

import pyk
from kevm_pyk.kompile import KompileTarget
from pyk.kbuild.utils import KVersion, k_version
from pyk.proof.reachability import APRProof
from pyk.proof.tui import APRProofViewer

from . import VERSION
from .cli import _create_argument_parser, read_toml_args
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
    foundry_state_diff,
    foundry_step_node,
    foundry_to_dot,
    foundry_unrefute_node,
    read_deployment_state,
)
from .kompile import foundry_kompile
from .options import ProveOptions, RPCOptions
from .prove import foundry_prove
from .solc_to_k import solc_compile, solc_to_k

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable
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
    args = read_toml_args(parser, args, sys.argv[2:]) if hasattr(args, 'config_file') else args
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
    _ignore_arg(kwargs, 'spec_module', f'--spec-module {kwargs["spec_module"]}')
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
    break_on_calls: bool = True,
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
    counterexample_info: bool = False,
    trace_rewrites: bool = False,
    auto_abstract_gas: bool = False,
    run_constructor: bool = False,
    fail_fast: bool = False,
    port: int | None = None,
    maude_port: int | None = None,
    use_gas: bool = False,
    deployment_state_path: Path | None = None,
    with_non_general_state: bool = False,
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

    results = foundry_prove(
        foundry=_load_foundry(foundry_root, bug_report),
        prove_options=prove_options,
        rpc_options=rpc_options,
        tests=tests,
        include_summaries=include_summaries,
    )
    failed = 0
    for proof in results:
        if proof.passed:
            print(f'PROOF PASSED: {proof.id}')
        else:
            failed += 1
            print(f'PROOF FAILED: {proof.id}')
            failure_log = None
            if isinstance(proof, APRProof):
                failure_log = proof.failure_info
            if failure_info and failure_log is not None:
                log = failure_log.print() + Foundry.help_info()
                for line in log:
                    print(line)

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
    counterexample_info: bool = False,
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
    foundry_refute_node(foundry=_load_foundry(foundry_root), test=test, node=node, version=version)


def exec_unrefute_node(foundry_root: Path, test: str, node: NodeIdLike, version: int | None, **kwargs: Any) -> None:
    foundry_unrefute_node(foundry=_load_foundry(foundry_root), test=test, node=node, version=version)


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

def _loglevel(args: Namespace) -> int:
    if hasattr(args, 'debug') and args.debug:
        return logging.DEBUG

    if hasattr(args, 'verbose') and args.verbose:
        return logging.INFO

    return logging.WARNING


if __name__ == '__main__':
    main()
