from __future__ import annotations

import json
import logging
import sys
from argparse import ArgumentParser
from collections.abc import Iterable
from os import chdir, getcwd
from typing import TYPE_CHECKING

import pyk
from kevm_pyk.cli import KOptions, node_id_like
from kevm_pyk.utils import arg_pair_of
from pyk.cli.args import LoggingOptions
from pyk.cli.utils import file_path
from pyk.cterm.symbolic import CTermSMTError
from pyk.kbuild.utils import KVersion, k_version
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.proof.tui import APRProofViewer
from pyk.utils import ensure_dir_path, run_process

from . import VERSION
from .cli import FoundryOptions, FoundryTestOptions, KontrolCLIArgs
from .foundry import (
    Foundry,
    GetModelOptions,
    LoadStateDiffOptions,
    MergeNodesOptions,
    MinimizeProofOptions,
    RefuteNodeOptions,
    RemoveNodeOptions,
    SectionEdgeOptions,
    ShowOptions,
    SimplifyNodeOptions,
    SplitNodeOptions,
    StepNodeOptions,
    ToDotOptions,
    UnrefuteNodeOptions,
    foundry_get_model,
    foundry_list,
    foundry_merge_nodes,
    foundry_minimize_proof,
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
from .kompile import BuildOptions, foundry_kompile
from .prove import ProveOptions, foundry_prove, parse_test_version_tuple
from .solc_to_k import SolcToKOptions, solc_compile, solc_to_k
from .utils import empty_lemmas_file_contents, kontrol_file_contents, write_to_file

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any, Final, TypeVar

    from pyk.cterm import CTerm
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


def generate_options(args: dict[str, Any]) -> LoggingOptions:
    command = args['command']
    options = {
        'load-state-diff': LoadStateDiffOptions(args),
        'version': VersionOptions(args),
        'compile': CompileOptions(args),
        'solc-to-k': SolcToKOptions(args),
        'build': BuildOptions(args),
        'prove': ProveOptions(args),
        'show': ShowOptions(args),
        'refute-node': RefuteNodeOptions(args),
        'unrefute-node': UnrefuteNodeOptions(args),
        'split-node': SplitNodeOptions(args),
        'to-dot': ToDotOptions(args),
        'list': ListOptions(args),
        'view-kcfg': ViewKcfgOptions(args),
        'remove-node': RemoveNodeOptions(args),
        'simplify-node': SimplifyNodeOptions(args),
        'step-node': StepNodeOptions(args),
        'merge-nodes': MergeNodesOptions(args),
        'section-edge': SectionEdgeOptions(args),
        'get-model': GetModelOptions(args),
        'minimize-proof': MinimizeProofOptions(args),
        'clean': CleanOptions(args),
        'init': InitOptions(args),
    }
    try:
        return options[command]
    except KeyError as err:
        raise ValueError(f'Unrecognized command: {command}') from err


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
    expected_k_version = KVersion.parse(f'v{pyk.__version__}')
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


class VersionOptions(LoggingOptions): ...


def exec_version(options: VersionOptions) -> None:
    print(f'Kontrol version: {VERSION}')


class CompileOptions(LoggingOptions):
    contract_file: Path


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


class ListOptions(LoggingOptions, KOptions, FoundryOptions): ...


def exec_list(options: ListOptions) -> None:
    stats = foundry_list(foundry=_load_foundry(options.foundry_root))
    print('\n'.join(stats))


class ViewKcfgOptions(FoundryTestOptions, LoggingOptions, FoundryOptions): ...


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


def exec_minimize_proof(options: MinimizeProofOptions) -> None:
    foundry_minimize_proof(foundry=_load_foundry(options.foundry_root), options=options)


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


class CleanOptions(FoundryOptions, LoggingOptions): ...


def exec_clean(options: CleanOptions) -> None:
    run_process(['forge', 'clean', '--root', str(options.foundry_root)], logger=_LOGGER)


class InitOptions(FoundryOptions, LoggingOptions):
    skip_forge: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'skip_forge': False,
        }


def exec_init(options: InitOptions) -> None:
    """
    Wrapper around forge init that adds files required for kontrol compatibility.

    TODO: --root does not work for forge install, so we're temporary using `chdir`.
    """

    if not options.skip_forge:
        run_process(['forge', 'init', str(options.foundry_root)], logger=_LOGGER)

    write_to_file(options.foundry_root / 'lemmas.k', empty_lemmas_file_contents())
    write_to_file(options.foundry_root / 'KONTROL.md', kontrol_file_contents())
    cwd = getcwd()
    chdir(options.foundry_root)
    run_process(
        ['forge', 'install', '--no-git', 'runtimeverification/kontrol-cheatcodes'],
        logger=_LOGGER,
    )
    chdir(cwd)


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
        default=None,
        action='store_true',
        help='Regenerate foundry.k even if it already exists.',
    )
    build.add_argument(
        '--rekompile',
        dest='rekompile',
        default=None,
        action='store_true',
        help='Rekompile foundry.k even if kompiled definition already exists.',
    )
    build.add_argument(
        '--no-forge-build',
        dest='no_forge_build',
        default=None,
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
        type=file_path,
        help='Path to JSON containing deployment addresses and its respective contract names',
    )
    state_diff_args.add_argument(
        '--condense-state-diff',
        dest='condense_state_diff',
        default=None,
        type=bool,
        help='Deploy state diff as a single file',
    )
    state_diff_args.add_argument(
        '--output-dir',
        dest='output_dir_name',
        type=str,
        help='Path to write state diff .sol files, relative to foundry root',
    )
    state_diff_args.add_argument(
        '--comment-generated-files',
        dest='comment_generated_file',
        type=str,
        help='Comment to write at the top of the auto generated state diff files',
    )
    state_diff_args.add_argument(
        '--license',
        dest='license',
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
        default=None,
        action='store_true',
        help='Reinitialize CFGs even if they already exist.',
    )
    prove_args.add_argument(
        '--setup-version',
        dest='setup_version',
        default=None,
        type=int,
        help='Instead of reinitializing the test setup together with the test proof, select the setup version to be reused during the proof.',
    )
    prove_args.add_argument(
        '--max-frontier-parallel',
        default=None,
        type=int,
        help='Maximum worker threads to use on a single proof to explore separate branches in parallel.',
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
        default=None,
        action='store_true',
        help='Include the contract constructor in the test execution.',
    )
    prove_args.add_argument(
        '--use-gas', dest='use_gas', default=None, action='store_true', help='Enables gas computation in KEVM.'
    )
    prove_args.add_argument(
        '--break-on-cheatcodes',
        dest='break_on_cheatcodes',
        default=None,
        action='store_true',
        help='Break on all Foundry rules.',
    )
    prove_args.add_argument(
        '--init-node-from',
        dest='deployment_state_path',
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
        default=None,
        action='store_true',
        help='Flag used by Simbolik to initialise the state of a non test function as if it was a test function.',
    )
    prove_args.add_argument(
        '--xml-test-report',
        dest='xml_test_report',
        default=None,
        action='store_true',
        help='Generate a JUnit XML report',
    )
    prove_args.add_argument(
        '--cse', dest='cse', default=None, action='store_true', help='Use Compositional Symbolic Execution'
    )
    prove_args.add_argument(
        '--hevm',
        dest='hevm',
        default=None,
        action='store_true',
        help='Use hevm success predicate instead of foundry to determine if a test is passing',
    )
    prove_args.add_argument(
        '--minimize-proofs', dest='minimize_proofs', default=False, action='store_true', help='Minimize obtained KCFGs'
    )
    prove_args.add_argument(
        '--evm-tracing',
        dest='evm_tracing',
        action='store_true',
        default=False,
        help='Trace opcode execution and store it in the configuration',
    )
    prove_args.add_argument(
        '--no-trace-storage',
        dest='trace_storage',
        action='store_false',
        default=True,
        help='If tracing is active, avoid storing storage information.',
    )
    prove_args.add_argument(
        '--no-trace-wordstack',
        dest='trace_wordstack',
        action='store_false',
        default=True,
        help='If tracing is active, avoid storing wordstack information.',
    )
    prove_args.add_argument(
        '--no-trace-memory',
        dest='trace_memory',
        action='store_false',
        default=True,
        help='If tracing is active, avoid storing memory information.',
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
        default=None,
        action='store_true',
        help='Strip output that is likely to change without the contract logic changing',
    )
    show_args.add_argument(
        '--to-kevm-claims',
        dest='to_kevm_claims',
        default=None,
        action='store_true',
        help='Generate a K module which can be run directly as KEVM claims for the given KCFG (best-effort).',
    )
    show_args.add_argument(
        '--kevm-claim-dir',
        dest='kevm_claim_dir',
        type=ensure_dir_path,
        help='Path to write KEVM claim files at.',
    )
    show_args.add_argument(
        '--use-hex-encoding',
        dest='use_hex_encoding',
        default=False,
        action='store_true',
        help='Print elements in hexadecimal encoding.',
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

    command_parser.add_parser(
        'minimize-proof',
        help='Minimize the KCFG of the proof for a given test.',
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
        '--replace', default=None, help='Replace the original node with the simplified variant in the graph.'
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
        '--repeat', type=int, help='How many node expansions to do from the given start node (>= 1).'
    )
    step_node.add_argument('--depth', type=int, help='How many steps to take from initial node on edge.')
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
    section_edge.add_argument('--sections', type=int, help='Number of sections to make from edge (>= 2).')

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
        '--pending', dest='pending', default=None, action='store_true', help='Also display models of pending nodes'
    )
    get_model.add_argument(
        '--failing', dest='failing', default=None, action='store_true', help='Also display models of failing nodes'
    )
    command_parser.add_parser(
        'clean',
        help='Remove the build artifacts and cache directories.',
        parents=[
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    init = command_parser.add_parser(
        'init',
        help='Create a new Forge project compatible with Kontrol',
        parents=[
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    init.add_argument(
        '--skip-forge',
        dest='skip_forge',
        default=False,
        action='store_true',
        help='Skip Forge initialisation and add only the files required for Kontrol (for already existing Forge projects).',
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
