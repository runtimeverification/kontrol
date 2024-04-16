from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

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
    port: int | None
    maude_port: int | None

    def __init__(
        self,
        *,
        use_booster: bool = True,
        kore_rpc_command: str | Iterable[str] | None = None,
        smt_timeout: int | None = None,
        smt_retry_limit: int | None = None,
        smt_tactic: str | None = None,
        trace_rewrites: bool = False,
        port: int | None = None,
        maude_port: int | None = None,
    ) -> None:
        if kore_rpc_command is None:
            kore_rpc_command = ('kore-rpc-booster',) if use_booster else ('kore-rpc',)
        elif isinstance(kore_rpc_command, str):
            kore_rpc_command = (kore_rpc_command,)
        else:
            kore_rpc_command = tuple(kore_rpc_command)
        object.__setattr__(self, 'use_booster', use_booster)
        object.__setattr__(self, 'kore_rpc_command', kore_rpc_command)
        object.__setattr__(self, 'smt_timeout', smt_timeout)
        object.__setattr__(self, 'smt_retry_limit', smt_retry_limit)
        object.__setattr__(self, 'smt_tactic', smt_tactic)
        object.__setattr__(self, 'trace_rewrites', trace_rewrites)
        object.__setattr__(self, 'port', port)
        object.__setattr__(self, 'maude_port', maude_port)


@dataclass(frozen=True)
class TraceOptions:
    active_tracing: bool
    trace_storage: bool
    trace_wordstack: bool
    trace_memory: bool

    def __init__(
        self,
        *,
        active_tracing: bool = False,
        trace_storage: bool = False,
        trace_wordstack: bool = False,
        trace_memory: bool = False,
    ) -> None:
        object.__setattr__(self, 'active_tracing', active_tracing)
        object.__setattr__(self, 'trace_storage', trace_storage)
        object.__setattr__(self, 'trace_wordstack', trace_wordstack)
        object.__setattr__(self, 'trace_memory', trace_memory)
