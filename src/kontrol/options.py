from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from kevm_pyk.cli import DisplayOptions, ExploreOptions, KCFGShowOptions, KOptions, KProveOptions
from kevm_pyk.kompile import KompileTarget
from pyk.cli.args import BugReportOptions, KompileOptions, LoggingOptions, Options, ParallelOptions, SMTOptions

if TYPE_CHECKING:
    from pyk.kcfg.kcfg import NodeIdLike


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
    }
    try:
        return options[command]
    except KeyError as err:
        raise ValueError(f'Unrecognized command: {command}') from err


def get_option_string_destination(command: str, option_string: str) -> str:
    option_string_destinations = {}
    match command:
        case 'load-state-diff':
            option_string_destinations = LoadStateDiffOptions.from_option_string()
        case 'version':
            option_string_destinations = VersionOptions.from_option_string()
        case 'compile':
            option_string_destinations = CompileOptions.from_option_string()
        case 'solc-to-k':
            option_string_destinations = SolcToKOptions.from_option_string()
        case 'build':
            option_string_destinations = BuildOptions.from_option_string()
        case 'prove':
            option_string_destinations = ProveOptions.from_option_string()
        case 'show':
            option_string_destinations = ShowOptions.from_option_string()
        case 'refute-node':
            option_string_destinations = RefuteNodeOptions.from_option_string()
        case 'unrefute-node':
            option_string_destinations = UnrefuteNodeOptions.from_option_string()
        case 'split-node':
            option_string_destinations = SplitNodeOptions.from_option_string()
        case 'to-dot':
            option_string_destinations = ToDotOptions.from_option_string()
        case 'list':
            option_string_destinations = ListOptions.from_option_string()
        case 'view-kcfg':
            option_string_destinations = ViewKcfgOptions.from_option_string()
        case 'remove-node':
            option_string_destinations = RemoveNodeOptions.from_option_string()
        case 'simplify-node':
            option_string_destinations = SimplifyNodeOptions.from_option_string()
        case 'step-node':
            option_string_destinations = StepNodeOptions.from_option_string()
        case 'merge-nodes':
            option_string_destinations = MergeNodesOptions.from_option_string()
        case 'section-edge':
            option_string_destinations = SectionEdgeOptions.from_option_string()
        case 'get-model':
            option_string_destinations = GetModelOptions.from_option_string()

    if option_string in option_string_destinations:
        return option_string_destinations[option_string]
    else:
        return option_string.replace('-', '_')


class CompileOptions(LoggingOptions):
    contract_file: Path


class FoundryOptions(Options):
    foundry_root: Path

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'foundry_root': Path('.'),
        }

    @staticmethod
    def from_option_string() -> dict[str, Any]:
        return {
            'foundry-project-root': 'foundry_root',
        }


class FoundryTestOptions(Options):
    test: str
    version: int | None

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'version': None,
        }

    @staticmethod
    def from_option_string() -> dict[str, Any]:
        return {
            'v': 'version',
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

    @staticmethod
    def from_option_string() -> dict[str, Any]:
        return {
            'require': 'requires',
            'module-import': 'imports',
        }


class KompileTargetOptions(Options):
    target: KompileTarget

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'target': KompileTarget.HASKELL,
        }


class ListOptions(LoggingOptions, KOptions, FoundryOptions): ...


class LoadStateDiffOptions(LoggingOptions, FoundryOptions):
    name: str
    accesses_file: Path
    contract_names: Path | None
    condense_state_diff: bool
    output_dir_name: str | None
    comment_generated_file: str
    license: str

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'contract_names': None,
            'condense_state_diff': False,
            'output_dir_name': None,
            'comment_generated_file': '// This file was autogenerated by running `kontrol load-state-diff`. Do not edit this file manually.\n',
            'license': 'UNLICENSED',
        }

    @staticmethod
    def from_option_string() -> dict[str, Any]:
        return {
            'output-dir': 'output_dir_name',
            'comment-generated-files': 'comment_generated_file',
        }


class MergeNodesOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    nodes: list[NodeIdLike]

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'nodes': [],
        }

    @staticmethod
    def from_option_string() -> dict[str, Any]:
        return {
            'node': 'nodes',
        }


class RefuteNodeOptions(LoggingOptions, FoundryTestOptions, FoundryOptions):
    node: NodeIdLike


class RemoveNodeOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    node: NodeIdLike


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


class SectionEdgeOptions(FoundryTestOptions, LoggingOptions, RpcOptions, BugReportOptions, SMTOptions, FoundryOptions):
    edge: tuple[str, str]
    sections: int

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'sections': 2,
        }


class ShowOptions(
    FoundryTestOptions,
    LoggingOptions,
    KOptions,
    KCFGShowOptions,
    DisplayOptions,
    FoundryOptions,
    RpcOptions,
    SMTOptions,
):
    omit_unstable_output: bool
    to_kevm_claims: bool
    kevm_claim_dir: Path | None
    use_hex_encoding: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'omit_unstable_output': False,
            'to_kevm_claims': False,
            'kevm_claim_dir': None,
            'use_hex_encoding': False,
            'counterexample_info': True,
        }


class SimplifyNodeOptions(
    FoundryTestOptions, LoggingOptions, SMTOptions, RpcOptions, BugReportOptions, DisplayOptions, FoundryOptions
):
    node: NodeIdLike
    replace: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'replace': False,
        }


class SolcToKOptions(LoggingOptions, KOptions, KGenOptions):
    contract_file: Path
    contract_name: str


class SplitNodeOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    node: NodeIdLike
    branch_condition: str


class StepNodeOptions(FoundryTestOptions, LoggingOptions, RpcOptions, BugReportOptions, SMTOptions, FoundryOptions):
    node: NodeIdLike
    repeat: int
    depth: int

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'repeat': 1,
            'depth': 1,
        }


class ToDotOptions(FoundryTestOptions, LoggingOptions, FoundryOptions): ...


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


class UnrefuteNodeOptions(LoggingOptions, FoundryTestOptions, FoundryOptions):
    node: NodeIdLike


class ViewKcfgOptions(FoundryTestOptions, LoggingOptions, FoundryOptions): ...


class VersionOptions(LoggingOptions): ...


class BuildOptions(LoggingOptions, KOptions, KGenOptions, KompileOptions, FoundryOptions, KompileTargetOptions):
    regen: bool
    rekompile: bool
    no_forge_build: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'regen': False,
            'rekompile': False,
            'no_forge_build': False,
        }


class GetModelOptions(FoundryTestOptions, LoggingOptions, RpcOptions, BugReportOptions, SMTOptions, FoundryOptions):
    nodes: list[NodeIdLike]
    pending: bool
    failing: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'nodes': [],
            'pending': False,
            'failing': False,
        }


class ProveOptions(
    LoggingOptions,
    ParallelOptions,
    KOptions,
    KProveOptions,
    SMTOptions,
    RpcOptions,
    BugReportOptions,
    ExploreOptions,
    FoundryOptions,
    TraceOptions,
):
    tests: list[tuple[str, int | None]]
    reinit: bool
    bmc_depth: int | None
    run_constructor: bool
    use_gas: bool
    setup_version: int | None
    break_on_cheatcodes: bool
    deployment_state_path: Path | None
    include_summaries: list[tuple[str, int | None]]
    with_non_general_state: bool
    xml_test_report: bool
    cse: bool
    hevm: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'tests': [],
            'reinit': False,
            'bmc_depth': None,
            'run_constructor': False,
            'use_gas': False,
            'break_on_cheatcodes': False,
            'deployment_state_path': None,
            'setup_version': None,
            'include_summaries': [],
            'with_non_general_state': False,
            'xml_test_report': False,
            'cse': False,
            'hevm': False,
        }

    @staticmethod
    def from_option_string() -> dict[str, Any]:
        return {
            'match-test': 'tests',
            'init-node-from': 'deployment_state_path',
            'include-summary': 'include_summaries',
        }
