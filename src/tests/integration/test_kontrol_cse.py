from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from kontrol.foundry import foundry_show
from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR, assert_or_update_show_output

if TYPE_CHECKING:
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport

    from kontrol.foundry import Foundry


FORGE_STD_REF: Final = '75f1746'


sys.setrecursionlimit(10**7)


ALL_DEPENDENCY_TESTS: Final = tuple((TEST_DATA_DIR / 'foundry-dependency-all').read_text().splitlines())
SKIPPED_DEPENDENCY_TESTS: Final = set((TEST_DATA_DIR / 'foundry-dependency-skip').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_DEPENDENCY_TESTS)
def test_foundry_dependency_automated(
    test_id: str,
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    update_expected_output: bool,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if test_id in SKIPPED_DEPENDENCY_TESTS:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    # Execution without CSE
    prove_options = ProveOptions(
        max_depth=10000,
        max_iterations=100,
        break_on_calls=False,
        bug_report=bug_report,
        fail_fast=False,
        workers=2,
    )

    foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=prove_options,
        rpc_options=RPCOptions(port=server.port, smt_timeout=500),
    )

    show_res = foundry_show(
        foundry,
        test=test_id,
        to_module=False,
        sort_collections=True,
        omit_unstable_output=True,
        pending=False,
        failing=False,
        failure_info=False,
        counterexample_info=False,
        port=server.port,
    )

    assert_or_update_show_output(
        show_res, TEST_DATA_DIR / f'show/{test_id}.no-cse.expected', update=update_expected_output
    )

    # Execution with CSE
    cse_prove_options = ProveOptions(
        max_depth=10000,
        max_iterations=100,
        bug_report=bug_report,
        break_on_calls=False,
        cse=True,
        reinit=True,
        fail_fast=False,
        workers=2,
    )

    foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=cse_prove_options,
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    cse_show_res = foundry_show(
        foundry,
        test=test_id,
        to_module=False,
        sort_collections=True,
        omit_unstable_output=True,
        pending=False,
        failing=False,
        failure_info=False,
        counterexample_info=False,
        port=server.port,
    )

    assert_or_update_show_output(
        cse_show_res, TEST_DATA_DIR / f'show/{test_id}.cse.expected', update=update_expected_output
    )
