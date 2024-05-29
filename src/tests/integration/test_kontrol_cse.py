from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from kontrol.foundry import ShowOptions, foundry_show
from kontrol.options import ProveOptions
from kontrol.prove import ConfigType, foundry_prove

from .utils import TEST_DATA_DIR, assert_or_update_show_output

if TYPE_CHECKING:
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport

    from kontrol.foundry import Foundry


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

    test_contract_name = test_id.split('.')[0]
    config_type = ConfigType.TEST_CONFIG if test_contract_name.endswith('Test') else ConfigType.SUMMARY_CONFIG

    if test_id in SKIPPED_DEPENDENCY_TESTS:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'max_depth': 10000,
                'max_iterations': 100,
                'bug_report': bug_report,
                'cse': True,
                'minimize_proofs': True,
                'fail_fast': False,
                'workers': 2,
                'port': server.port,
                'tests': [(test_id, None)],
                'config_type': config_type,
                'run_constructor': True,
            }
        ),
    )

    cse_show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test_id,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': False,
                'failing': False,
                'failure_info': False,
                'counterexample_info': False,
                'port': server.port,
            }
        ),
    )

    assert_or_update_show_output(
        cse_show_res, TEST_DATA_DIR / f'show/{test_id}.cse.expected', update=update_expected_output
    )
