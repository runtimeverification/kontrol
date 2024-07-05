from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from pyk.utils import single

from kontrol.options import ProveOptions
from kontrol.prove import foundry_prove

from .utils import assert_fail, assert_pass

if TYPE_CHECKING:
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport

    from kontrol.foundry import Foundry


sys.setrecursionlimit(10**7)

ALL_HEVM_TESTS_PASSING: Final = (
    'HevmTests.prove_require_assert_true',
    'HevmTests.proveFail_require_assert',
    'HevmTests.prove_revert',
)


@pytest.mark.parametrize('test', ALL_HEVM_TESTS_PASSING)
def test_hevm_prove_passing(
    test: str,
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'counterexample_info': True,
                'bug_report': bug_report,
                'hevm': True,
                'port': server.port,
                'tests': [(test, None)],
            }
        ),
    )

    assert_pass(test, single(prove_res))


ALL_HEVM_TESTS_FAILING: Final = (
    'HevmTests.prove_require_assert_false',
    'HevmTests.proveFail_all_branches',
)


@pytest.mark.parametrize('test', ALL_HEVM_TESTS_FAILING)
def test_hevm_prove_failing(
    test: str,
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'counterexample_info': True,
                'bug_report': bug_report,
                'hevm': True,
                'port': server.port,
            }
        ),
    )

    assert_fail(test, single(prove_res))
