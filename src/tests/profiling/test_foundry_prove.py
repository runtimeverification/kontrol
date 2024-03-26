from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from kontrol.kompile import foundry_kompile
from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

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
        foundry_kompile(foundry=foundry, includes=())

    with profile('prove.prof', sort_keys=('cumtime', 'tottime'), limit=100):
        foundry_prove(
            foundry,
            tests=[('AssertTest.test_revert_branch', None)],
            prove_options=ProveOptions(
                bug_report=bug_report,
            ),
            rpc_options=RPCOptions(
                smt_timeout=300,
                smt_retry_limit=10,
                use_booster=not no_use_booster,
            ),
        )
