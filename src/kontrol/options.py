from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kevm_pyk.cli import (
    DisplayOptions,
    EVMChainOptions,
    ExploreOptions,
    KCFGShowOptions,
    KOptions,
    KProveOptions,
    list_of,
    node_id_like,
)
from kevm_pyk.kompile import KompileTarget
from kevm_pyk.utils import arg_pair_of
from pyk.cli.args import BugReportOptions, KompileOptions, LoggingOptions, Options, ParallelOptions, SMTOptions
from pyk.cli.utils import dir_path, file_path
from pyk.utils import ensure_dir_path

from .utils import parse_test_version_tuple

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyk.kcfg.kcfg import NodeIdLike


class ConfigType(Enum):
    TEST_CONFIG = 'TEST_CONFIG'
    SUMMARY_CONFIG = 'SUMMARY_CONFIG'


class FoundryOptions(Options):
    foundry_root: Path
    enum_constraints: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'foundry_root': Path('.'),
            'enum_constraints': False,
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
    log_succ_rewrites: bool
    log_fail_rewrites: bool
    kore_rpc_command: str | None
    use_booster: bool
    port: int | None
    lemmas: str | None

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'log_succ_rewrites': True,
            'log_fail_rewrites': False,
            'kore_rpc_command': None,
            'use_booster': True,
            'port': None,
            'lemmas': None,
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return {
            'log-rewrites': 'log_succ_rewrites',
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


class CleanOptions(FoundryOptions, LoggingOptions):
    proofs: bool
    old_proofs: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'proofs': False,
            'old_proofs': False,
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return FoundryOptions.from_option_string() | LoggingOptions.from_option_string()

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return FoundryOptions.get_argument_type() | LoggingOptions.get_argument_type()


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
    def from_option_string() -> dict[str, str]:
        return LoggingOptions.from_option_string()

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return LoggingOptions.get_argument_type() | {
            'project_root': Path,
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


class ListOptions(LoggingOptions, KOptions, FoundryOptions):
    @staticmethod
    def from_option_string() -> dict[str, str]:
        return FoundryOptions.from_option_string() | LoggingOptions.from_option_string() | KOptions.from_option_string()

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return FoundryOptions.get_argument_type() | LoggingOptions.get_argument_type() | KOptions.get_argument_type()


class LoadStateOptions(LoggingOptions, FoundryOptions):
    name: str
    accesses_file: Path
    contract_names: Path | None
    condense_state_diff: bool
    output_dir_name: str | None
    comment_generated_file: str
    license: str
    from_state_diff: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'contract_names': None,
            'condense_state_diff': False,
            'output_dir_name': None,
            'comment_generated_file': '// This file was autogenerated by running `kontrol load-state`. Do not edit this file manually.\n',
            'license': 'UNLICENSED',
            'from_state_diff': False,
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


class MinimizeProofOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    merge: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'merge': False,
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
        )

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            FoundryOptions.get_argument_type()
            | LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
        )


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
    EVMChainOptions,
):
    tests: list[tuple[str, int | None]]
    reinit: bool
    bmc_depth: int | None
    run_constructor: bool
    setup_version: int | None
    break_on_cheatcodes: bool
    recorded_diff_state_path: Path | None
    recorded_dump_state_path: Path | None
    include_summaries: list[tuple[str, int | None]]
    with_non_general_state: bool
    xml_test_report: bool
    xml_test_report_name: str
    cse: bool
    hevm: bool
    minimize_proofs: bool
    max_frontier_parallel: int
    config_type: ConfigType
    hide_status_bar: bool
    remove_old_proofs: bool
    optimize_performance: int | None
    stack_checks: bool
    extra_module: str | None
    symbolic_caller: bool

    def __init__(self, args: dict[str, Any]) -> None:
        super().__init__(args)
        self.apply_optimizations()

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'tests': [],
            'reinit': False,
            'bmc_depth': None,
            'run_constructor': False,
            'usegas': False,
            'break_on_cheatcodes': False,
            'recorded_diff_state_path': None,
            'recorded_dump_state_path': None,
            'setup_version': None,
            'include_summaries': [],
            'with_non_general_state': False,
            'xml_test_report': False,
            'xml_test_report_name': 'kontrol_prove_report.xml',
            'cse': False,
            'hevm': False,
            'minimize_proofs': False,
            'max_frontier_parallel': 1,
            'config_type': ConfigType.TEST_CONFIG,
            'hide_status_bar': False,
            'remove_old_proofs': False,
            'optimize_performance': None,
            'stack_checks': True,
            'extra_module': None,
            'symbolic_caller': False,
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
            | EVMChainOptions.from_option_string()
            | {
                'match-test': 'tests',
                'init-node-from-diff': 'recorded_diff_state_path',
                'init-node-from-dump': 'recorded_dump_state_path',
                'include-summary': 'include_summaries',
            }
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
            | EVMChainOptions.get_argument_type()
            | {
                'match-test': list_of(parse_test_version_tuple),
                'init-node-from-diff': file_path,
                'init-node-from-dump': file_path,
                'include-summary': list_of(parse_test_version_tuple),
            }
        )

    def apply_optimizations(self) -> None:
        """Applies a series of performance optimizations based on the value of the
        `optimize_performance` attribute.

        If `optimize_performance` is not `None`, this method will adjust several
        internal parameters to enhance performance. The integer value of `optimize_performance`
        is used to set the level of parallelism for frontier exploration and maintenance rate.
        """
        if self.optimize_performance is not None:
            self.assume_defined = True
            self.log_succ_rewrites = False
            self.max_frontier_parallel = self.optimize_performance
            self.maintenance_rate = 64
            self.smt_timeout = 120000
            self.smt_retry_limit = 0
            self.max_depth = 100000
            self.max_iterations = 10000
            self.stack_checks = False

    def __str__(self) -> str:
        """
        Generate a string representation of the instance, including attributes from inherited classes.

        The first line collects all attributes that are directly set on the instance.
        The loop is required to iterate over all parent classes and fetch attributes set by the `default` method.

        Default values from parent classes will only be used if the attribute is not explicitly set.

        :return: String representation of the instance.
        """
        options_dict = {**self.__dict__}

        for parent in self.__class__.__bases__:
            if hasattr(parent, 'default'):
                parent_defaults = parent.default()
                for key, value in parent_defaults.items():
                    if key not in options_dict:
                        options_dict[key] = value

        options_str = ', '.join(f'{key}: {value}' for key, value in options_dict.items())
        return f'ProveOptions({options_str})'


class RefuteNodeOptions(LoggingOptions, FoundryTestOptions, FoundryOptions):
    node: NodeIdLike

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
        )

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
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
        )

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
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | SMTOptions.from_option_string()
        )

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
    to_kevm_rules: bool
    kevm_claim_dir: Path | None
    use_hex_encoding: bool
    expand_config: bool
    minimize_kcfg: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'omit_unstable_output': False,
            'to_kevm_claims': False,
            'to_kevm_rules': False,
            'kevm_claim_dir': None,
            'use_hex_encoding': False,
            'counterexample_info': True,
            'expand_config': False,
            'minimize_kcfg': False,
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | KOptions.from_option_string()
            | KCFGShowOptions.from_option_string()
            | DisplayOptions.from_option_string()
            | RpcOptions.from_option_string()
            | SMTOptions.from_option_string()
        )

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
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | SMTOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | DisplayOptions.from_option_string()
        )

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


class SplitNodeOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    node: NodeIdLike
    branch_condition: str

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
        )

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
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | SMTOptions.from_option_string()
        )

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


class UnrefuteNodeOptions(LoggingOptions, FoundryTestOptions, FoundryOptions):
    node: NodeIdLike

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
        )

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


class VersionOptions(LoggingOptions):
    @staticmethod
    def from_option_string() -> dict[str, str]:
        return LoggingOptions.from_option_string()

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return LoggingOptions.get_argument_type()


class ViewKcfgOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):

    use_hex_encoding: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'use_hex_encoding': False,
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
        )

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            FoundryOptions.get_argument_type()
            | LoggingOptions.get_argument_type()
            | FoundryTestOptions.get_argument_type()
        )


class BuildOptions(LoggingOptions, KOptions, KompileOptions, FoundryOptions, KompileTargetOptions):
    regen: bool
    rekompile: bool
    forge_build: bool
    silence_warnings: bool
    metadata: bool
    keccak_lemmas: bool
    auxiliary_lemmas: bool
    requires: list[str]
    imports: list[str]

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'o2': True,
            'regen': False,
            'rekompile': False,
            'forge_build': True,
            'silence_warnings': True,
            'metadata': True,
            'keccak_lemmas': True,
            'auxiliary_lemmas': False,
            'requires': [],
            'imports': [],
        }

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | KOptions.from_option_string()
            | KompileOptions.from_option_string()
            | KompileTargetOptions.from_option_string()
            | {
                'require': 'requires',
                'module-import': 'imports',
            }
        )

    @staticmethod
    def get_argument_type() -> dict[str, Callable]:
        return (
            FoundryOptions.get_argument_type()
            | LoggingOptions.get_argument_type()
            | KOptions.get_argument_type()
            | KompileOptions.get_argument_type()
            | KompileTargetOptions.get_argument_type()
            | {
                'require': list_of(str),
                'module-import': list_of(str),
            }
        )

    def __str__(self) -> str:
        """
        Generate a string representation of the instance, including attributes from inherited classes.

        The first line collects all attributes that are directly set on the instance.
        The loop is required to iterate over all parent classes and fetch attributes set by the `default` method.

        Default values from parent classes will only be used if the attribute is not explicitly set.

        :return: String representation of the instance.
        """
        options_dict = {**self.__dict__}

        for parent in self.__class__.__bases__:
            if hasattr(parent, 'default'):
                parent_defaults = parent.default()
                for key, value in parent_defaults.items():
                    if key not in options_dict:
                        options_dict[key] = value

        options_str = ', '.join(f'{key}: {value}' for key, value in options_dict.items())
        return f'BuildOptions({options_str})'
