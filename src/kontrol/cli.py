from __future__ import annotations

import logging
from argparse import ArgumentParser
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tomli
from kevm_pyk.cli import KEVMCLIArgs, node_id_like
from kevm_pyk.kompile import KompileTarget
from pyk.cli.args import Options
from pyk.cli.utils import dir_path

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Callable
    from typing import Any, Final, TypeVar

    T = TypeVar('T')


class FoundryOptions(Options):
    foundry_root: Path

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'foundry_root': Path('.'),
        }


class FoundryTestOptions(Options):
    test: str
    version: int | None

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'version': None,
        }


class KGenOptions(Options):
    requires: list[str]
    imports: list[str]

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'requires': [],
            'imports': [],
        }


class KompileTargetOptions(Options):
    target: KompileTarget

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'target': KompileTarget.HASKELL,
        }


class TraceOptions(Options):
    active_tracing: bool
    trace_storage: bool
    trace_wordstack: bool
    trace_memory: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'active_tracing': False,
            'trace_storage': False,
            'trace_wordstack': False,
            'trace_memory': False,
        }


class RpcOptions(Options):
    trace_rewrites: bool
    kore_rpc_command: str | None
    use_booster: bool
    port: int | None
    maude_port: int | None

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'trace_rewrites': False,
            'kore_rpc_command': None,
            'use_booster': True,
            'port': None,
            'maude_port': None,
        }


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
    def config_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--config',
            dest='config_file',
            type=file_path,
            default=Path('./kontrol.toml'),
            help='Path to Kontrol config file.',
        )
        args.add_argument(
            '--config-profile',
            dest='config_profile',
            default='default',
            help='Config profile to be used.',
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
            kontrol_cli_args.config_args,
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
            kontrol_cli_args.config_args,
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
            kontrol_cli_args.config_args,
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
        type=_parse_test_version_tuple,
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
        type=_parse_test_version_tuple,
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

    show_args = command_parser.add_parser(
        'show',
        help='Print the CFG for a given proof.',
        parents=[
            kontrol_cli_args.config_args,
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
        parents=[
            kontrol_cli_args.config_args,
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
        ],
    )

    command_parser.add_parser(
        'list',
        help='List information about CFGs on disk',
        parents=[
            kontrol_cli_args.config_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.k_args,
            kontrol_cli_args.foundry_args,
        ],
    )

    command_parser.add_parser(
        'view-kcfg',
        help='Explore a given proof in the KCFG visualizer.',
        parents=[
            kontrol_cli_args.config_args,
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
        ],
    )

    remove_node = command_parser.add_parser(
        'remove-node',
        help='Remove a node and its successors.',
        parents=[
            kontrol_cli_args.config_args,
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    remove_node.add_argument('node', type=node_id_like, help='Node to remove CFG subgraph from.')

    refute_node = command_parser.add_parser(
        'refute-node',
        help='Refute a node and add its refutation as a subproof.',
        parents=[
            kontrol_cli_args.config_args,
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    refute_node.add_argument('node', type=node_id_like, help='Node to refute.')

    unrefute_node = command_parser.add_parser(
        'unrefute-node',
        help='Disable refutation of a node and remove corresponding refutation subproof.',
        parents=[
            kontrol_cli_args.config_args,
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
        ],
    )
    unrefute_node.add_argument('node', type=node_id_like, help='Node to unrefute.')

    simplify_node = command_parser.add_parser(
        'simplify-node',
        help='Simplify a given node, and potentially replace it.',
        parents=[
            kontrol_cli_args.config_args,
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
            kontrol_cli_args.config_args,
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
            kontrol_cli_args.config_args,
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
            kontrol_cli_args.config_args,
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
            kontrol_cli_args.config_args,
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


def read_toml_args(parser: ArgumentParser, args: Namespace, cmd_args: list[str]) -> Namespace:
    def canonicalize_option(long_opt: str) -> None:
        if long_opt in ['ccopt', 'I', 'O0', 'O1', 'O2', 'O3']:
            toml_commands.append('-' + long_opt)
        elif long_opt == 'includes':
            toml_commands.extend(['-I' + a_path for a_path in toml_profile_args[long_opt]])
            toml_profile_args[long_opt] = ''
        elif long_opt == 'optimization-level':
            level = toml_profile_args[long_opt] if toml_profile_args[long_opt] >= 0 else 0
            level = level if toml_profile_args[long_opt] <= 3 else 3
            toml_profile_args[long_opt] = ''
            toml_commands.append('-O' + str(level))
        elif long_opt == 'counterexample-information':
            toml_commands.append('--counterexample-information')
            toml_commands.append('--failure-information')
        else:
            toml_commands.append('--' + long_opt)

    def canonicalize_negative_logic_option(long_opt: str) -> None:
        switching_options = [
            'emit-json',
            'minimize',
            'use-booster',
            'failure-information',
            'break-on-calls',
            'always-check-subsumption',
            'expand-macros',
            'always-check-subsumption',
            'fast-check-subsumption',
            'gas',
            'post-exec-simplify',
            'counterexample-informaiton',
            'fail-fast',
            'llvm-kompile',
        ]
        if long_opt in switching_options:
            toml_commands.append('--no-' + long_opt)
        elif long_opt[:4] == 'no-' and long_opt[3:] in switching_options:
            toml_commands.append('--' + long_opt[3:])

    def get_profile(toml_profile: dict[str, Any], profile_list: list[str]) -> dict[str, Any]:
        if len(profile_list) == 0 or profile_list[0] not in toml_profile.keys():
            return toml_profile
        elif len(profile_list) == 1:
            return toml_profile[profile_list[0]]
        return get_profile(toml_profile[profile_list[0]], profile_list[1:])

    toml_args = {}
    if args.config_file.is_file():
        with open(args.config_file, 'rb') as config_file:
            try:
                toml_args = tomli.load(config_file)
            except tomli.TOMLDecodeError:
                _LOGGER.error(
                    'Input config file is not in TOML format, ignoring the file and carrying on with the provided command line agruments'
                )

    toml_commands = [args.command]
    toml_profile_args = (
        get_profile(toml_args[args.command], args.config_profile.split('.')) if args.command in toml_args.keys() else {}
    )

    for a_key in toml_profile_args:
        if a_key in ['config', 'profile'] or isinstance(toml_profile_args[a_key], dict):
            continue
        elif type(toml_profile_args[a_key]) is not bool:
            canonicalize_option(a_key)
            if len(str(toml_profile_args[a_key])) > 0:
                toml_commands.append(str(toml_profile_args[a_key]))
        elif toml_profile_args[a_key]:
            canonicalize_option(a_key)
        else:
            canonicalize_negative_logic_option(a_key)

    return parser.parse_args(toml_commands + cmd_args)
