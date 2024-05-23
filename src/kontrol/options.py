from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from kevm_pyk.cli import DisplayOptions, ExploreOptions, KCFGShowOptions, KOptions, KProveOptions
from kevm_pyk.kompile import KompileTarget
from pyk.cli.args import BugReportOptions, KompileOptions, LoggingOptions, Options, ParallelOptions, SMTOptions

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyk.utils import BugReport

    from .deployment import DeploymentStateEntry


@dataclass(frozen=True)
class ProveOptions:
    auto_abstract_gas: bool
    bug_report: BugReport | None
    bmc_depth: int | None
    max_depth: int
    break_every_step: bool
    break_on_jumpi: bool
    break_on_calls: bool
    break_on_storage: bool
    break_on_basic_blocks: bool
    break_on_cheatcodes: bool
    workers: int
    counterexample_info: bool
    max_iterations: int | None
    run_constructor: bool
    fail_fast: bool
    reinit: bool
    setup_version: int | None
    use_gas: bool
    deployment_state_entries: Iterable[DeploymentStateEntry] | None
    active_symbolik: bool
    cse: bool
    hevm: bool
    minimize_proofs: bool
    trace_options: TraceOptions | None

    def __init__(
        self,
        *,
        auto_abstract_gas: bool = False,
        bug_report: BugReport | None = None,
        bmc_depth: int | None = None,
        max_depth: int = 1000,
        break_every_step: bool = False,
        break_on_jumpi: bool = False,
        break_on_calls: bool = False,
        break_on_storage: bool = False,
        break_on_basic_blocks: bool = False,
        break_on_cheatcodes: bool = False,
        workers: int = 1,
        counterexample_info: bool = True,
        max_iterations: int | None = None,
        run_constructor: bool = False,
        fail_fast: bool = True,
        reinit: bool = False,
        setup_version: int | None = None,
        use_gas: bool = False,
        deployment_state_entries: list[DeploymentStateEntry] | None = None,
        active_symbolik: bool = False,
        cse: bool = False,
        hevm: bool = False,
        minimize_proofs: bool = False,
        trace_options: TraceOptions | None = None,
    ) -> None:
        object.__setattr__(self, 'auto_abstract_gas', auto_abstract_gas)
        object.__setattr__(self, 'bug_report', bug_report)
        object.__setattr__(self, 'bmc_depth', bmc_depth)
        object.__setattr__(self, 'max_depth', max_depth)
        object.__setattr__(self, 'break_every_step', break_every_step)
        object.__setattr__(self, 'break_on_jumpi', break_on_jumpi)
        object.__setattr__(self, 'break_on_calls', break_on_calls)
        object.__setattr__(self, 'break_on_storage', break_on_storage)
        object.__setattr__(self, 'break_on_basic_blocks', break_on_basic_blocks)
        object.__setattr__(self, 'break_on_cheatcodes', break_on_cheatcodes)
        object.__setattr__(self, 'workers', workers)
        object.__setattr__(self, 'counterexample_info', counterexample_info)
        object.__setattr__(self, 'max_iterations', max_iterations)
        object.__setattr__(self, 'run_constructor', run_constructor)
        object.__setattr__(self, 'fail_fast', fail_fast)
        object.__setattr__(self, 'reinit', reinit)
        object.__setattr__(self, 'setup_version', setup_version)
        object.__setattr__(self, 'use_gas', use_gas)
        object.__setattr__(self, 'deployment_state_entries', deployment_state_entries)
        object.__setattr__(self, 'active_symbolik', active_symbolik)
        object.__setattr__(self, 'cse', cse)
        object.__setattr__(self, 'hevm', hevm)
        object.__setattr__(self, 'minimize_proofs', minimize_proofs)
        object.__setattr__(self, 'trace_options', trace_options)


@dataclass(frozen=True)
class RPCOptions:
    use_booster: bool
    kore_rpc_command: tuple[str, ...]
    smt_timeout: int | None
    smt_retry_limit: int | None
    smt_tactic: str | None
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

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | SMTOptions.from_option_string()
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
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | RpcOptions.from_option_string()
            | KOptions.from_option_string()
            | KCFGShowOptions.from_option_string()
            | DisplayOptions.from_option_string()
            | SMTOptions.from_option_string()
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
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | DisplayOptions.from_option_string()
            | SMTOptions.from_option_string()
        )


class SolcToKOptions(LoggingOptions, KOptions, KGenOptions):
    contract_file: Path
    contract_name: str

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return KOptions.from_option_string() | KGenOptions.from_option_string() | LoggingOptions.from_option_string()


class SplitNodeOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):
    node: NodeIdLike
    branch_condition: str

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
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
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | SMTOptions.from_option_string()
        )


class ToDotOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
        )


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

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
        )


class ViewKcfgOptions(FoundryTestOptions, LoggingOptions, FoundryOptions):

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
        )


class VersionOptions(LoggingOptions):

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return LoggingOptions.from_option_string()


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

    @staticmethod
    def from_option_string() -> dict[str, str]:
        return (
            FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | KOptions.from_option_string()
            | KGenOptions.from_option_string()
            | KompileOptions.from_option_string()
            | KompileTargetOptions.from_option_string()
        )


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
            FoundryOptions.from_option_string()
            | FoundryTestOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | SMTOptions.from_option_string()
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
        return (
            {
                'match-test': 'tests',
                'init-node-from': 'deployment_state_path',
                'include-summary': 'include_summaries',
            }
            | FoundryOptions.from_option_string()
            | LoggingOptions.from_option_string()
            | ParallelOptions.from_option_string()
            | KOptions.from_option_string()
            | KProveOptions.from_option_string()
            | SMTOptions.from_option_string()
            | RpcOptions.from_option_string()
            | BugReportOptions.from_option_string()
            | ExploreOptions.from_option_string()
            | TraceOptions.from_option_string()
        )
