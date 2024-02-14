from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyk.kore.rpc import FallbackReason
    from pyk.utils import BugReport

    from .deployment import SummaryEntry
    from kevm_pyk.options import ProveOptions


@dataclass(frozen=True)
class KontrolProveOptions(ProveOptions):
    bmc_depth: int | None
    break_on_cheatcodes: bool
    run_constructor: bool
    use_gas: bool
    summary_entries: Iterable[SummaryEntry] | None

    def __init__(
        self,
        *,
        bmc_depth: int | None = None,
        break_on_cheatcodes: bool | None = None,
        run_constructor: bool | None = None,
        use_gas: bool | None = None,
        failure_info: bool | None = None,
        summary_entries: list[SummaryEntry] | None = None,
        fast_check_subsumption: bool | None = None,
        always_check_subsumption: bool | None = None,
        post_exec_simplify: bool | None = None,
        fallback_on: Iterable[str | FallbackReason] | None = None,
        interim_simplification: int | None = None,
        **kwargs,
    ) -> None:
        object.__setattr__(self, 'bmc_depth', bmc_depth)
        object.__setattr__(self, 'break_on_cheatcodes', bool(break_on_cheatcodes))
        object.__setattr__(self, 'run_constructor', bool(run_constructor))
        object.__setattr__(self, 'use_gas', bool(use_gas))
        object.__setattr__(self, 'summary_entries', summary_entries)
        super().__init__(kwargs)
