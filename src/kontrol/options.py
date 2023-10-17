from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from pyk.utils import BugReport

    from .foundry import Foundry


@dataclass
class GlobalOptions:
    foundry: Foundry
    auto_abstract_gas: bool
    bug_report: BugReport | None
    kore_rpc_command: str | Iterable[str] | None
    llvm_definition_dir: Path | None
    smt_timeout: int | None
    smt_retry_limit: int | None
    trace_rewrites: bool
    simplify_init: bool
    bmc_depth: int | None
    max_depth: int
    break_every_step: bool
    break_on_jumpi: bool
    break_on_calls: bool
    workers: int
    counterexample_info: bool
    max_iterations: int | None
    run_constructor: bool
    fail_fast: bool
