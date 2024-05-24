from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from kevm_pyk.cli import DisplayOptions, ExploreOptions, KCFGShowOptions, KOptions, KProveOptions, list_of, node_id_like
from kevm_pyk.kompile import KompileTarget
from kevm_pyk.utils import arg_pair_of
from pyk.cli.args import BugReportOptions, KompileOptions, LoggingOptions, Options, ParallelOptions, SMTOptions
from pyk.cli.utils import dir_path, file_path
from pyk.utils import ensure_dir_path

from .utils import parse_test_version_tuple

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyk.kcfg.kcfg import NodeIdLike


class FoundryOptions(Options):
    foundry_root: Path

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'foundry_root': Path('.'),
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return {
            'foundry-project-root': 'foundry_root',
        }

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return {
            'foundry-project-root': dir_path,
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


class CleanOptions(FoundryOptions, LoggingOptions): ...


class CompileOptions(LoggingOptions):
    contract_file: Path

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return LoggingOptions.get_argument_type() | {
            'contract_file': file_path,
        }


class FoundryTestOptions(Options):
    test: str
    version: int | None

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'version': None,
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

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            LoggingOptions.from_option_string()
            | FoundryOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | SMTOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | {
                'node': 'nodes',
            }
        )

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            FoundryTestOptions.get_argument_type()
            | LoggingOptions.get_argument_type()
            | RpcOptions.get_argument_type()
            | BugReportOptions.get_argument_type()
            | SMTOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | {
                'node': list_of(node_id_like),
            }
        )


class InitOptions(LoggingOptions):
    project_root: Path
    skip_forge: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'project_root': Path.cwd(),
            'skip_forge': False,
        }

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return LoggingOptions.get_argument_type() | {
            'project_root': Path,
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
    def from_option_string() -> dict[str, str]:
        return {
            'require': 'requires',
            'module-import': 'imports',
        }

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return {
            'require': list_of(str),
            'module-import': list_of(str),
        }


class KompileTargetOptions(Options):
    target: KompileTarget

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'target': KompileTarget.HASKELL,
        }

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return {
            'target': KompileTarget,
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
    def from_option_string() -> dict[str, str]:
        return (
            LoggingOptions.from_option_string()
            | FoundryOptions.from_option_string()
            | {'output-dir': 'output_dir_name', 'comment-generated-files': 'comment_generated_file'}
        )

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | {
                'accesses_file': file_path,
                'contract-names': file_path,
            }
        )


class MergeNodesOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    nodes: list[NodeIdLike]

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'nodes': [],
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            LoggingOptions.from_option_string()
            | FoundryOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | {
                'node': 'nodes',
            }
        )

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | {
                'node': list_of(node_id_like),
            }
        )


class MinimizeProofOptions(FoundryTestOptions, LoggingOptions, FoundryOptions): ...


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
    minimize_proofs: bool
    max_frontier_parallel: int

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
            'minimize_proofs': False,
            'max_frontier_parallel': 1,
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            LoggingOptions.from_option_string()
            | ParallelOptions.from_option_string()
            | KOptions.from_option_string()
            | KProveOptions.from_option_string()
            | SMTOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | ExploreOptions.from_option_string()
            | FoundryOptions.from_option_string()
            | TraceOptions.from_option_string()
            | {'match-test': 'tests', 'init-node-from': 'deployment_state_path', 'include-summary': 'include_summaries'}
        )

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | ParallelOptions.get_argument_type()
            | KOptions.get_argument_type()
            | KProveOptions.get_argument_type()
            | SMTOptions.get_argument_type()
            | RpcOptions.get_argument_type()
            | BugReportOptions.get_argument_type()
            | ExploreOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | TraceOptions.get_argument_type()
            | {
                'match-test': list_of(parse_test_version_tuple),
                'init-node-from': file_path,
                'include-summary': list_of(parse_test_version_tuple),
            }
        )


class RefuteNodeOptions(LoggingOptions, FoundryTestOptions, FoundryOptions):
    node: NodeIdLike

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | {
                'node': node_id_like,
            }
        )


class RemoveNodeOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    node: NodeIdLike

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | {
                'node': node_id_like,
            }
        )


class SectionEdgeOptions(FoundryTestOptions, LoggingOptions, RpcOptions, BugReportOptions, SMTOptions, FoundryOptions):
    edge: tuple[str, str]
    sections: int

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'sections': 2,
        }

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | BugReportOptions.get_argument_type()
            | SMTOptions.get_argument_type()
            | RpcOptions.get_argument_type()
            | {
                'edge': arg_pair_of(str, str),
            }
        )


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

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            FoundryTestOptions.get_argument_type()
            | LoggingOptions.get_argument_type()
            | KOptions.get_argument_type()
            | KCFGShowOptions.get_argument_type()
            | DisplayOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | RpcOptions.get_argument_type()
            | SMTOptions.get_argument_type()
            | {
                'kevm-claim-dir': ensure_dir_path,
            }
        )


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

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | BugReportOptions.get_argument_type()
            | SMTOptions.get_argument_type()
            | DisplayOptions.get_argument_type()
            | RpcOptions.get_argument_type()
            | {
                'node': node_id_like,
            }
        )


class SolcToKOptions(LoggingOptions, KOptions, KGenOptions):
    contract_file: Path
    contract_name: str

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | KOptions.get_argument_type()
            | KGenOptions.get_argument_type()
            | {
                'contract_file': file_path,
            }
        )


class SplitNodeOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    node: NodeIdLike
    branch_condition: str

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | {
                'node': node_id_like,
            }
        )


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

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | BugReportOptions.get_argument_type()
            | SMTOptions.get_argument_type()
            | {
                'node': node_id_like,
            }
        )


class ToDotOptions(FoundryTestOptions, LoggingOptions, FoundryOptions): ...


class UnrefuteNodeOptions(LoggingOptions, FoundryTestOptions, FoundryOptions):
    node: NodeIdLike

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
            | FoundryOptions.get_argument_type()
            | {
                'node': node_id_like,
            }
        )


class VersionOptions(LoggingOptions): ...


class ViewKcfgOptions(FoundryTestOptions, LoggingOptions, FoundryOptions): ...


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
