from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterable
from os import chdir, getcwd
from typing import TYPE_CHECKING

import pyk
from pyk.cterm.symbolic import CTermSMTError
from pyk.kbuild.utils import KVersion, k_version
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.proof.tui import APRProofViewer
from pyk.utils import run_process

from . import VERSION
from .cli import _create_argument_parser
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
from .options import generate_options
from .prove import foundry_prove
from .solc_to_k import solc_compile, solc_to_k
from .utils import empty_lemmas_file_contents, kontrol_file_contents, write_to_file

if TYPE_CHECKING:
    from argparse import Namespace
    from pathlib import Path
    from typing import Any, Final, TypeVar

    from pyk.cterm import CTerm
    from pyk.kcfg.tui import KCFGElem
    from pyk.utils import BugReport

    from .kompile import BuildOptions
    from .options import (
        CompileOptions,
        GetModelOptions,
        ListOptions,
        LoadStateDiffOptions,
        MergeNodesOptions,
        RefuteNodeOptions,
        RemoveNodeOptions,
        SectionEdgeOptions,
        ShowOptions,
        SimplifyNodeOptions,
        SolcToKOptions,
        SplitNodeOptions,
        StepNodeOptions,
        ToDotOptions,
        UnrefuteNodeOptions,
        VersionOptions,
        ViewKcfgOptions,
    )
    from .prove import ProveOptions

    T = TypeVar('T')

_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


def _ignore_arg(args: dict[str, Any], arg: str, cli_option: str) -> None:
    if arg in args:
        if args[arg] is not None:
            _LOGGER.warning(f'Ignoring command-line option: {cli_option}')
        args.pop(arg)


def _load_foundry(foundry_root: Path, bug_report: BugReport | None = None, use_hex_encoding: bool = False) -> Foundry:
    try:
        foundry = Foundry(foundry_root=foundry_root, bug_report=bug_report, use_hex_encoding=use_hex_encoding)
    except FileNotFoundError:
        print(
            f'File foundry.toml not found in: {str(foundry_root)!r}. Are you running kontrol in a Foundry project?',
            file=sys.stderr,
        )
        sys.exit(127)
    return foundry


def main() -> None:
    sys.setrecursionlimit(15000000)
    parser = _create_argument_parser()
    args = parser.parse_args()
    logging.basicConfig(level=_loglevel(args), format=_LOG_FORMAT)

    _check_k_version()

    stripped_args = {
        key: val for (key, val) in vars(args).items() if val is not None and not (isinstance(val, Iterable) and not val)
    }
    options = generate_options(stripped_args)

    executor_name = 'exec_' + args.command.lower().replace('-', '_')
    if executor_name not in globals():
        raise AssertionError(f'Unimplemented command: {args.command}')

    execute = globals()[executor_name]
    execute(options)


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


def exec_load_state_diff(options: LoadStateDiffOptions) -> None:
    foundry_state_diff(
        options=options,
        foundry=_load_foundry(options.foundry_root),
    )


def exec_version(options: VersionOptions) -> None:
    print(f'Kontrol version: {VERSION}')


def exec_compile(options: CompileOptions) -> None:
    res = solc_compile(options.contract_file)
    print(json.dumps(res))


def exec_solc_to_k(options: SolcToKOptions) -> None:
    k_text = solc_to_k(options)
    print(k_text)


def exec_build(options: BuildOptions) -> None:
    foundry_kompile(
        options=options,
        foundry=_load_foundry(options.foundry_root),
    )


def exec_prove(options: ProveOptions) -> None:
    deployment_state_entries = (
        read_deployment_state(options.deployment_state_path) if options.deployment_state_path else None
    )

    try:
        results = foundry_prove(
            foundry=_load_foundry(options.foundry_root, options.bug_report),
            options=options,
            deployment_state_entries=deployment_state_entries,
        )
    except CTermSMTError as err:
        raise RuntimeError(
            f'SMT solver error; SMT timeout occured. SMT timeout parameter is currently set to {options.smt_timeout}ms, you may increase it using "--smt-timeout" command line argument. Related KAST pattern provided below:\n{err.message}'
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
            if options.failure_info and failure_log is not None:
                log = failure_log.print() + (Foundry.help_info() if not options.hevm else Hevm.help_info(proof.id))
                for line in log:
                    print(line)
            refuted_nodes = list(proof.node_refutations.keys())
            if len(refuted_nodes) > 0:
                print(f'The proof cannot be completed while there are refuted nodes: {refuted_nodes}.')
                print('Either unrefute the nodes or discharge the corresponding refutation subproofs.')

    sys.exit(1 if failed else 0)


def exec_show(options: ShowOptions) -> None:
    output = foundry_show(
        foundry=_load_foundry(options.foundry_root, use_hex_encoding=options.use_hex_encoding),
        options=options,
    )
    print(output)


def exec_refute_node(options: RefuteNodeOptions) -> None:
    foundry = _load_foundry(options.foundry_root)
    refutation = foundry_refute_node(foundry=foundry, options=options)

    if refutation:
        claim, _ = refutation.to_claim('refuted-' + str(options.node))
        print('\nClaim for the refutation:\n')
        print(foundry.kevm.pretty_print(claim))
        print('\n')
    else:
        raise ValueError(f'Unable to refute node for test {options.test}: {options.node}')


def exec_unrefute_node(options: UnrefuteNodeOptions) -> None:
    foundry_unrefute_node(
        foundry=_load_foundry(options.foundry_root),
        options=options,
    )


def exec_split_node(options: SplitNodeOptions) -> None:
    node_ids = foundry_split_node(
        foundry=_load_foundry(options.foundry_root),
        options=options,
    )

    print(f'Node {options.node} has been split into {node_ids} on condition {options.branch_condition}.')


def exec_to_dot(options: ToDotOptions) -> None:
    foundry_to_dot(foundry=_load_foundry(options.foundry_root), options=options)


def exec_list(options: ListOptions) -> None:
    stats = foundry_list(foundry=_load_foundry(options.foundry_root))
    print('\n'.join(stats))


def exec_view_kcfg(options: ViewKcfgOptions) -> None:
    foundry = _load_foundry(options.foundry_root, use_hex_encoding=True)
    test_id = foundry.get_test_id(options.test, options.version)
    contract_name, _ = test_id.split('.')
    proof = foundry.get_apr_proof(test_id)

    def _short_info(cterm: CTerm) -> Iterable[str]:
        return foundry.short_info_for_contract(contract_name, cterm)

    def _custom_view(elem: KCFGElem) -> Iterable[str]:
        return foundry.custom_view(contract_name, elem)

    node_printer = foundry_node_printer(foundry, contract_name, proof)
    viewer = APRProofViewer(proof, foundry.kevm, node_printer=node_printer, custom_view=_custom_view)
    viewer.run()


def exec_remove_node(options: RemoveNodeOptions) -> None:
    foundry_remove_node(
        foundry=_load_foundry(options.foundry_root),
        options=options,
    )


def exec_simplify_node(options: SimplifyNodeOptions) -> None:

    pretty_term = foundry_simplify_node(
        foundry=_load_foundry(options.foundry_root, options.bug_report),
        options=options,
    )
    print(f'Simplified:\n{pretty_term}')


def exec_step_node(options: StepNodeOptions) -> None:
    foundry_step_node(
        foundry=_load_foundry(options.foundry_root, options.bug_report),
        options=options,
    )


def exec_merge_nodes(options: MergeNodesOptions) -> None:
    foundry_merge_nodes(
        foundry=_load_foundry(options.foundry_root),
        options=options,
    )


def exec_section_edge(options: SectionEdgeOptions) -> None:

    foundry_section_edge(
        foundry=_load_foundry(options.foundry_root, options.bug_report),
        options=options,
    )


def exec_get_model(options: GetModelOptions) -> None:

    output = foundry_get_model(
        foundry=_load_foundry(options.foundry_root),
        options=options,
    )
    print(output)


def exec_clean(
    foundry_root: Path,
    **kwargs: Any,
) -> None:
    run_process(['forge', 'clean', '--root', str(foundry_root)], logger=_LOGGER)


def exec_init(
    foundry_root: Path,
    skip_forge: bool,
    **kwargs: Any,
) -> None:
    """
    Wrapper around forge init that adds files required for kontrol compatibility.

    TODO: --root does not work for forge install, so we're temporary using `chdir`.
    """

    if not skip_forge:
        run_process(['forge', 'init', str(foundry_root)], logger=_LOGGER)

    write_to_file(foundry_root / 'lemmas.k', empty_lemmas_file_contents())
    write_to_file(foundry_root / 'KONTROL.md', kontrol_file_contents())
    cwd = getcwd()
    chdir(foundry_root)
    run_process(
        ['forge', 'install', '--no-git', 'runtimeverification/kontrol-cheatcodes'],
        logger=_LOGGER,
    )
    chdir(cwd)


# Helpers


def _loglevel(args: Namespace) -> int:
    if hasattr(args, 'debug') and args.debug:
        return logging.DEBUG

    if hasattr(args, 'verbose') and args.verbose:
        return logging.INFO

    return logging.WARNING


if __name__ == '__main__':
    main()
