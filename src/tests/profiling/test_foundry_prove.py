from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from kontrol.kompile import foundry_kompile
from kontrol.options import BuildOptions, ProveOptions
from kontrol.prove import foundry_prove

from ..utils import forge_build
from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path

    from pyk.testing import Profiler
    from pyk.utils import BugReport


sys.setrecursionlimit(10**7)


def test_foundy_prove(profile: Profiler, bug_report: BugReport | None, tmp_path: Path, force_sequential: bool) -> None:
    foundry_root = tmp_path / 'foundry'
    foundry = forge_build(TEST_DATA_DIR, foundry_root)

    with profile('kompile.prof', sort_keys=('cumtime', 'tottime'), limit=15):
        foundry_kompile(
            BuildOptions(
                {'includes': (), 'metadata': False},
            ),
            foundry=foundry,
        )

    with profile('prove.prof', sort_keys=('cumtime', 'tottime'), limit=100):
        foundry_prove(
            options=ProveOptions(
                {
                    'bug_report': bug_report,
                    'use_booster': True,
                    'tests': [('AssertTest.test_revert_branch', None)],
                    'force_sequential': force_sequential,
                }
            ),
            foundry=foundry,
        )
