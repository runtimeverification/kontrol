from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from kontrol.foundry import foundry_show
from kontrol.options import ProveOptions, RPCOptions, TraceOptions
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR, assert_or_update_show_output

if TYPE_CHECKING:
    from pathlib import Path

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport

    from kontrol.foundry import Foundry


sys.setrecursionlimit(10**7)


ALL_TRACE_FILE: Path = TEST_DATA_DIR / 'foundry-trace-all'
SKIPPED_TRACE_FILE: Path = TEST_DATA_DIR / 'foundry-trace-skip'

SKIPPED_TRACE_TESTS = set(SKIPPED_TRACE_FILE.read_text().splitlines())


def parse_trace_options(trace_wordstack: str, trace_memory: str, trace_storage: str) -> TraceOptions:
    def _str_to_bool(s: str) -> bool:
        return s.lower() in ['true', '1', 't', 'y', 'yes']

    return TraceOptions(
        active_tracing=True,
        trace_wordstack=_str_to_bool(trace_wordstack),
        trace_memory=_str_to_bool(trace_memory),
        trace_storage=_str_to_bool(trace_storage),
    )


ALL_TRACE_TESTS_WITH_OPTIONS = [
    (
        line_contents[0],
        parse_trace_options(
            trace_wordstack=line_contents[1], trace_memory=line_contents[2], trace_storage=line_contents[3]
        ),
    )
    for line in ALL_TRACE_FILE.read_text().splitlines()
    if (line_contents := line.split(','))
]


@pytest.mark.parametrize('test_id,trace_options', ALL_TRACE_TESTS_WITH_OPTIONS)
def test_foundry_trace(
    test_id: str,
    trace_options: TraceOptions,
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    update_expected_output: bool,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if test_id in SKIPPED_TRACE_TESTS:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_options = ProveOptions(
        max_depth=10000,
        max_iterations=100,
        bug_report=bug_report,
        fail_fast=False,
        trace_options=trace_options,
    )

    foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=prove_options,
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    trace_show_res = foundry_show(
        foundry,
        test=test_id,
        to_module=True,
        sort_collections=True,
        omit_unstable_output=True,
        pending=True,
        failing=True,
        failure_info=True,
        port=server.port,
    )

    assert_or_update_show_output(
        trace_show_res, TEST_DATA_DIR / f'show/{test_id}.trace.expected', update=update_expected_output
    )
