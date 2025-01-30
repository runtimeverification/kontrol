from __future__ import annotations

from argparse import ArgumentParser
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kevm_pyk.cli import KEVMCLIArgs, node_id_like
from kevm_pyk.utils import arg_pair_of
from pyk.cli.utils import dir_path, file_path
from pyk.utils import ensure_dir_path

from .options import (
    BuildOptions,
    CleanOptions,
    CompileOptions,
    GetModelOptions,
    InitOptions,
    ListOptions,
    LoadStateOptions,
    MergeNodesOptions,
    MinimizeProofOptions,
    ProveOptions,
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
from .prove import ConfigType, parse_test_version_tuple

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from .options import LoggingOptions

    T = TypeVar('T')


def generate_options(args: dict[str, Any]) -> LoggingOptions:
    command = args['command']
    options = {
        'load-state': LoadStateOptions(args),
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


def get_option_string_destination(command: str, option_string: str) -> str:
    option_string_destinations = {}
    options = {
        'load-state': LoadStateOptions.from_option_string(),
        'version': VersionOptions.from_option_string(),
        'compile': CompileOptions.from_option_string(),
        'solc-to-k': SolcToKOptions.from_option_string(),
        'build': BuildOptions.from_option_string(),
        'prove': ProveOptions.from_option_string(),
        'show': ShowOptions.from_option_string(),
        'refute-node': RefuteNodeOptions.from_option_string(),
        'unrefute-node': UnrefuteNodeOptions.from_option_string(),
        'split-node': SplitNodeOptions.from_option_string(),
        'to-dot': ToDotOptions.from_option_string(),
        'list': ListOptions.from_option_string(),
        'view-kcfg': ViewKcfgOptions.from_option_string(),
        'remove-node': RemoveNodeOptions.from_option_string(),
        'simplify-node': SimplifyNodeOptions.from_option_string(),
        'step-node': StepNodeOptions.from_option_string(),
        'merge-nodes': MergeNodesOptions.from_option_string(),
        'section-edge': SectionEdgeOptions.from_option_string(),
        'get-model': GetModelOptions.from_option_string(),
        'minimize-proof': MinimizeProofOptions.from_option_string(),
        'clean': CleanOptions.from_option_string(),
        'init': InitOptions.from_option_string(),
    }
    option_string_destinations = options[command]
    return option_string_destinations.get(option_string, option_string.replace('-', '_'))


def get_argument_type_setter(command: str, option_string: str) -> Callable[[str], Any]:
    option_types = {}
    options = {
        'load-state': LoadStateOptions.get_argument_type(),
        'version': VersionOptions.get_argument_type(),
        'compile': CompileOptions.get_argument_type(),
        'solc-to-k': SolcToKOptions.get_argument_type(),
        'build': BuildOptions.get_argument_type(),
        'prove': ProveOptions.get_argument_type(),
        'show': ShowOptions.get_argument_type(),
        'refute-node': RefuteNodeOptions.get_argument_type(),
        'unrefute-node': UnrefuteNodeOptions.get_argument_type(),
        'split-node': SplitNodeOptions.get_argument_type(),
        'to-dot': ToDotOptions.get_argument_type(),
        'list': ListOptions.get_argument_type(),
        'view-kcfg': ViewKcfgOptions.get_argument_type(),
        'remove-node': RemoveNodeOptions.get_argument_type(),
        'simplify-node': SimplifyNodeOptions.get_argument_type(),
        'step-node': StepNodeOptions.get_argument_type(),
        'merge-nodes': MergeNodesOptions.get_argument_type(),
        'section-edge': SectionEdgeOptions.get_argument_type(),
        'get-model': GetModelOptions.get_argument_type(),
        'minimize-proof': MinimizeProofOptions.get_argument_type(),
        'clean': CleanOptions.get_argument_type(),
        'init': InitOptions.get_argument_type(),
    }
    option_types = options[command]
    return option_types.get(option_string, (lambda x: x))


class ConfigArgs:
    @cached_property
    def config_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--config-file',
            dest='config_file',
            type=file_path,
            default=None,
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
        args.add_argument(
            '--enum-constraints',
            dest='enum_constraints',
            default=None,
            action='store_true',
            help='Add constraints for enum function arguments and storage slots.',
        )
        return args

    @cached_property
    def foundry_test_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument('test', type=str, help='Test to run')
        args.add_argument('--version', type=int, required=False, help='Version of the test to use')
        return args

    @cached_property
    def k_gen_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--require',
            dest='requires',
            action='append',
            help='Extra K requires to include in generated output.',
        )
        args.add_argument(
            '--module-import',
            dest='imports',
            action='append',
            help='Extra modules to import into generated main module.',
        )
        return args

    @cached_property
    def rpc_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--no-log-rewrites',
            dest='log_succ_rewrites',
            default=None,
            action='store_false',
            help='Do not log traces of any simplification and rewrite rule application.',
        )
        args.add_argument(
            '--log-fail-rewrites',
            dest='log_fail_rewrites',
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
            config_args.config_args,
        ],
    )
    build.add_argument(
        '--no-O2',
        dest='o2',
        default=None,
        action='store_false',
        help='Do not use optimization level 2.',
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
        dest='forge_build',
        default=None,
        action='store_false',
        help="Do not call 'forge build' during kompilation.",
    )
    build.add_argument(
        '--no-silence-warnings',
        dest='silence_warnings',
        default=None,
        action='store_false',
        help='Do not silence K compiler warnings.',
    )
    build.add_argument(
        '--no-metadata',
        dest='metadata',
        default=None,
        action='store_false',
        help='Do not append cbor or bytecode_hash metadata to bytecode.',
    )
    build.add_argument(
        '--no-keccak-lemmas',
        dest='keccak_lemmas',
        default=None,
        action='store_false',
        help='Do not include assumptions on keccak properties.',
    )
    build.add_argument(
        '--auxiliary-lemmas',
        dest='auxiliary_lemmas',
        default=None,
        action='store_true',
        help='Include auxiliary Kontrol lemmas.',
    )

    state_diff_args = command_parser.add_parser(
        'load-state',
        help='Generate a state diff summary from an account access dict',
        parents=[
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )
    state_diff_args.add_argument('name', type=str, help='Generated contract name')
    state_diff_args.add_argument('accesses_file', type=file_path, help='Path to state file')
    state_diff_args.add_argument(
        '--contract-names',
        dest='contract_names',
        type=file_path,
        help='Path to JSON containing deployment addresses and its respective contract names',
    )
    state_diff_args.add_argument(
        '--condense-state',
        dest='condense_state',
        type=bool,
        help='Recreate state as a single file',
    )
    state_diff_args.add_argument(
        '--output-dir',
        dest='output_dir_name',
        type=str,
        help='Path to write state .sol files, relative to foundry root',
    )
    state_diff_args.add_argument(
        '--comment-generated-files',
        dest='comment_generated_file',
        type=str,
        help='Comment to write at the top of the auto generated state files',
    )
    state_diff_args.add_argument(
        '--license',
        dest='license',
        type=str,
        help='License for the auto generated contracts',
    )
    state_diff_args.add_argument(
        '--from-state-diff',
        dest='from_state_diff',
        default=None,
        action='store_true',
        help='Indicate if the JSON comes from vm.stopAndReturnStateDiff and not vm.dumpState',
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
            kontrol_cli_args.evm_chain_args,
            config_args.config_args,
        ],
    )
    prove_args.add_argument(
        '--match-test',
        '--mt',
        type=parse_test_version_tuple,
        dest='tests',
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
        type=int,
        help='Instead of reinitializing the test setup together with the test proof, select the setup version to be reused during the proof.',
    )
    prove_args.add_argument(
        '--max-frontier-parallel',
        type=int,
        help='Maximum worker threads to use on a single proof to explore separate branches in parallel.',
    )
    prove_args.add_argument(
        '--bmc-depth',
        dest='bmc_depth',
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
        '--use-gas', dest='usegas', default=None, action='store_true', help='Enables gas computation in KEVM.'
    )
    prove_args.add_argument(
        '--config-type', default=None, type=ConfigType, help='Config type', choices=list(ConfigType)
    )
    prove_args.add_argument(
        '--hide-status-bar',
        dest='hide_status_bar',
        default=None,
        action='store_true',
        help='Disables the proof status bar.',
    )
    prove_args.add_argument(
        '--break-on-cheatcodes',
        dest='break_on_cheatcodes',
        default=None,
        action='store_true',
        help='Break on all Foundry rules.',
    )
    prove_args.add_argument(
        '--init-node-from-diff',
        dest='recorded_diff_state_path',
        type=file_path,
        help='Path to JSON file produced by vm.stopAndReturnStateDiff.',
    )
    prove_args.add_argument(
        '--init-node-from-dump',
        dest='recorded_dump_state_path',
        type=file_path,
        help='Path to JSON file produced by vm.dumpState.',
    )
    prove_args.add_argument(
        '--include-summary',
        type=parse_test_version_tuple,
        dest='include_summaries',
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
        '--xml-test-report-name',
        dest='xml_test_report_name',
        default=None,
        help='Specify the filename for the JUnit XML report',
    )
    prove_args.add_argument(
        '--cse', dest='cse', action='store_true', default=None, help='Use Compositional Symbolic Execution'
    )
    prove_args.add_argument(
        '--hevm',
        dest='hevm',
        default=None,
        action='store_true',
        help='Use hevm success predicate instead of foundry to determine if a test is passing',
    )
    prove_args.add_argument(
        '--minimize-proofs', dest='minimize_proofs', default=None, action='store_true', help='Minimize obtained KCFGs'
    )
    prove_args.add_argument(
        '--evm-tracing',
        dest='active_tracing',
        default=None,
        action='store_true',
        help='Trace opcode execution and store it in the configuration',
    )
    prove_args.add_argument(
        '--no-trace-storage',
        dest='trace_storage',
        default=None,
        action='store_false',
        help='If tracing is active, avoid storing storage information.',
    )
    prove_args.add_argument(
        '--no-trace-wordstack',
        dest='trace_wordstack',
        default=None,
        action='store_false',
        help='If tracing is active, avoid storing wordstack information.',
    )
    prove_args.add_argument(
        '--no-trace-memory',
        dest='trace_memory',
        default=None,
        action='store_false',
        help='If tracing is active, avoid storing memory information.',
    )
    prove_args.add_argument(
        '--remove-old-proofs',
        dest='remove_old_proofs',
        default=None,
        action='store_true',
        help='Remove all outdated KCFGs.',
    )
    prove_args.add_argument(
        '--optimize-performance',
        type=int,
        default=None,
        dest='optimize_performance',
        help=(
            'Optimize performance for proof execution. Takes the number of parallel threads to be used. '
            "Will overwrite other settings of 'assume-defined', 'log-success-rewrites', 'max-frontier-parallel', "
            "'maintenance-rate', 'smt-timeout', 'smt-retry-limit', 'max-depth', 'max-iterations', and 'no-stack-checks'."
        ),
    )
    prove_args.add_argument(
        '--no-stack-checks',
        dest='stack_checks',
        default=None,
        action='store_false',
        help=(
            'Optimize KEVM execution by removing stack overflow/underflow checks. '
            'Assumes running Solidity-compiled bytecode cannot result in a stack overflow/underflow.'
        ),
    )
    prove_args.add_argument(
        '--extra-module',
        dest='extra_module',
        default=None,
        help=(
            'File and extra module to include for verification (which must import FOUNDRY-MAIN module).'
            'Format is <file>:<module name>.'
        ),
    )
    prove_args.add_argument(
        '--fork-url',
        dest='fork_url',
        default=None,
        help=('Fetch state over a remote endpoint instead of starting from an abstract state'),
    )
    prove_args.add_argument(
        '--fork-block-number',
        dest='fork_block_number',
        default=None,
        help=('Fetch state from a specific block number over a remote endpoint'),
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
        '--to-kevm-rules',
        dest='to_kevm_rules',
        default=None,
        action='store_true',
        help='Generate a K module which can be used to optimize KEVM execution (best-effort).',
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
        default=None,
        action='store_true',
        help='Print elements in hexadecimal encoding.',
    )
    show_args.add_argument(
        '--expand-config',
        dest='expand_config',
        default=None,
        action='store_true',
        help='When printing nodes, always show full bytecode in  code and program cells, and do not hide jumpDests cell.',
    )
    show_args.add_argument(
        '--minimize-kcfg',
        dest='minimize_kcfg',
        default=None,
        action='store_true',
        help='Run KCFG minimization routine before displaying it.',
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

    view_kcfg_args = command_parser.add_parser(
        'view-kcfg',
        help='Explore a given proof in the KCFG visualizer.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )

    view_kcfg_args.add_argument(
        '--use-hex-encoding',
        dest='use_hex_encoding',
        default=None,
        action='store_true',
        help='Print elements in hexadecimal encoding.',
    )

    minimize_proof_args = command_parser.add_parser(
        'minimize-proof',
        help='Minimize the KCFG of the proof for a given test.',
        parents=[
            kontrol_cli_args.foundry_test_args,
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )
    minimize_proof_args.add_argument(
        '--merge',
        dest='merge',
        default=None,
        action='store_true',
        help='Merge the nodes of the KCFG into a successful branch and a revert branch.',
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
    simplify_node.add_argument('--replace', help='Replace the original node with the simplified variant in the graph.')

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
        action='append',
        help='List of nodes to display the models of.',
    )
    get_model.add_argument(
        '--pending', dest='pending', default=None, action='store_true', help='Also display models of pending nodes'
    )
    get_model.add_argument(
        '--failing', dest='failing', default=None, action='store_true', help='Also display models of failing nodes'
    )
    clean = command_parser.add_parser(
        'clean',
        help='Remove the build artifacts and cache directories.',
        parents=[
            kontrol_cli_args.logging_args,
            kontrol_cli_args.foundry_args,
            config_args.config_args,
        ],
    )
    clean.add_argument(
        '--proofs',
        dest='proofs',
        action='store_true',
        default=None,
        help='Clean proofs directory.',
    )
    clean.add_argument(
        '--old-proofs',
        dest='old_proofs',
        action='store_true',
        default=None,
        help='Clean outdated proofs.',
    )
    init = command_parser.add_parser(
        'init',
        help='Create a new Forge project compatible with Kontrol',
        parents=[
            kontrol_cli_args.logging_args,
            config_args.config_args,
        ],
    )
    init.add_argument(
        dest='project_root',
        nargs='?',
        type=Path,
        help='Name of the project to be initialized. If missing, the current directory is used.',
    )

    init.add_argument(
        '--skip-forge',
        dest='skip_forge',
        default=None,
        action='store_true',
        help='Skip Forge initialisation and add only the files required for Kontrol (for already existing Forge projects).',
    )

    return parser
