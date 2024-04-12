from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from kontrol.kompile import BuildOptions, foundry_kompile
from kontrol.prove import ProveOptions, foundry_prove

from ..utils import forge_build
from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path

    from pyk.testing import Profiler
    from pyk.utils import BugReport


sys.setrecursionlimit(10**7)


def test_foundy_prove(profile: Profiler, no_use_booster: bool, bug_report: BugReport | None, tmp_path: Path) -> None:
    foundry_root = tmp_path / 'foundry'
    foundry = forge_build(TEST_DATA_DIR, foundry_root)

    with profile('kompile.prof', sort_keys=('cumtime', 'tottime'), limit=15):
        foundry_kompile(BuildOptions({'includes': ()}), foundry=foundry)

    with profile('prove.prof', sort_keys=('cumtime', 'tottime'), limit=100):
        foundry_prove(
            options=ProveOptions(
                {
                    'bug_report': bug_report,
                    'use_booster': not no_use_booster,
                    'tests': [('AssertTest.test_revert_branch', None)],
                }
            ),
            foundry=foundry,
        )
