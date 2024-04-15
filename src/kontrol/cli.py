from __future__ import annotations

import logging
from argparse import ArgumentParser
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomli
from kevm_pyk.cli import KEVMCLIArgs, node_id_like
from kevm_pyk.kompile import KompileTarget
from kevm_pyk.utils import arg_pair_of
from pyk.cli.utils import dir_path, ensure_dir_path, file_path

from .utils import parse_test_version_tuple
from .options import get_option_string_destination

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Callable
    from typing import Final, TypeVar

    T = TypeVar('T')

_LOGGER: Final = logging.getLogger(__name__)


class ConfigArgs:
    @cached_property
    def config_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--config-file',
            dest='config_file',
            type=file_path,
            default=Path('./pyk.toml'),
            help='Path to Pyk config file.',
        )
        args.add_argument(
            '--config-profile',
            dest='config_profile',
            default='default',
            help='Config profile to be used.',
        )
        return args


class KontrolCLIArgs(KEVMCLIArgs):
    @cached_property
    def foundry_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--foundry-project-root',
            dest='foundry_root',
            type=dir_path,
            help='Path to Foundry project root directory.',
        )
        return args

    @cached_property
    def foundry_test_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument('test', type=str, help='Test to run')
        args.add_argument('--version', type=int, default=None, required=False, help='Version of the test to use')
        return args

    @cached_property
    def k_gen_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--require',
            dest='requires',
            default=[],
            action='append',
            help='Extra K requires to include in generated output.',
        )
        args.add_argument(
            '--module-import',
            dest='imports',
            default=[],
            action='append',
            help='Extra modules to import into generated main module.',
        )
        return args

    @cached_property
    def kompile_target_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--target',
            type=KompileTarget,
            choices=[KompileTarget.HASKELL, KompileTarget.MAUDE],
            help='[haskell|maude]',
        )
        return args

    @cached_property
    def rpc_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--trace-rewrites',
            dest='trace_rewrites',
            default=None,
            action='store_true',
            help='Log traces of all simplification and rewrite rule applications.',
        )
        args.add_argument(
            '--kore-rpc-command',
            dest='kore_rpc_command',
            type=str,
            help='Custom command to start RPC server.',
        )
        args.add_argument(
            '--use-booster',
            dest='use_booster',
            default=None,
            action='store_true',
            help='Use the booster RPC server instead of kore-rpc (default).',
        )
        args.add_argument(
            '--no-use-booster',
            dest='use_booster',
            default=None,
            action='store_false',
            help='Do not use the booster RPC server instead of kore-rpc.',
        )
        args.add_argument(
            '--port',
            dest='port',
            type=int,
            help='Use existing RPC server on named port.',
        )
        args.add_argument(
            '--maude-port',
            dest='maude_port',
            type=int,
            help='Use existing Maude RPC server on named port.',
        )
        return args


def _create_argument_parser() -> ArgumentParser:
    def list_of(elem_type: Callable[[str], T], delim: str = ';') -> Callable[[str], list[T]]:
        def parse(s: str) -> list[T]:
            return [elem_type(elem) for elem in s.split(delim)]

        return parse

    kontrol_cli_args = KontrolCLIArgs()
    config_args = ConfigArgs()
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
            config_args.config_args,
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
            config_args.config_args,
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
        parents=[kontrol_cli_args.foundry_args, config_args.config_args],
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
            config_args.config_args,
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
            config_args.config_args,
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
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )

    command_parser.add_parser(
        'list',
        help='List information about CFGs on disk',
        parents=[
            kontrol_cli_args.logging_args,
            kontrol_cli_args.k_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )

    command_parser.add_parser(
        'view-kcfg',
        help='Explore a given proof in the KCFG visualizer.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )

    remove_node = command_parser.add_parser(
        'remove-node',
        help='Remove a node and its successors.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )
    remove_node.add_argument('node', type=node_id_like, help='Node to remove CFG subgraph from.')

    refute_node = command_parser.add_parser(
        'refute-node',
        help='Refute a node and add its refutation as a subproof.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )
    refute_node.add_argument('node', type=node_id_like, help='Node to refute.')

    unrefute_node = command_parser.add_parser(
        'unrefute-node',
        help='Disable refutation of a node and remove corresponding refutation subproof.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )
    unrefute_node.add_argument('node', type=node_id_like, help='Node to unrefute.')

    split_node = command_parser.add_parser(
        'split-node',
        help='Split a node on a given branch condition.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
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
            config_args.config_args,
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
            config_args.config_args,
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
            config_args.config_args,
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
            config_args.config_args,
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
            config_args.config_args,
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
        parents=[kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args, config_args.config_args],
    )
    init = command_parser.add_parser(
        'init',
        help='Create a new Forge project compatible with Kontrol',
        parents=[kontrol_cli_args.logging_args, kontrol_cli_args.foundry_args, config_args.config_args],
    )
    init.add_argument(
        '--skip-forge',
        dest='skip_forge',
        default=False,
        action='store_true',
        help='Skip Forge initialisation and add only the files required for Kontrol (for already existing Forge projects).',
    )

    return parser

def parse_toml_args(args: Namespace) -> dict[str, Any]:
    def get_profile(toml_profile: dict[str, Any], profile_list: list[str]) -> dict[str, Any]:
        if len(profile_list) == 0 or profile_list[0] not in toml_profile:
            return {k: v for k, v in toml_profile.items() if type(v) is not dict}
        elif len(profile_list) == 1:
            return {k: v for k, v in toml_profile[profile_list[0]].items() if type(v) is not dict}
        return get_profile(toml_profile[profile_list[0]], profile_list[1:])

    toml_args: dict[str, Any] = {}
    if not hasattr(args, 'config_file') or not args.config_file.is_file():
        return {}

    with open(args.config_file, 'rb') as config_file:
        try:
            toml_args = tomli.load(config_file)
        except tomli.TOMLDecodeError:
            _LOGGER.error(
                'Input config file is not in TOML format, ignoring the file and carrying on with the provided command line agruments'
            )

    toml_args = (
        get_profile(toml_args[args.command], args.config_profile.split('.')) if args.command in toml_args else {}
    )

    toml_adj_args: dict[str, Any] = {}
    for k, v in toml_args.items():
        opt_string = get_option_string_destination(args.command, k)
        if opt_string[:3] == 'no_':
            toml_adj_args[opt_string[3:]] = not v
        elif k == 'optimization-level':
            level = toml_args[k] if toml_args[k] >= 0 else 0
            level = level if toml_args[k] <= 3 else 3
            toml_adj_args['-o' + str(level)] = True
        else:
            toml_adj_args[opt_string] = v

    return toml_adj_args
