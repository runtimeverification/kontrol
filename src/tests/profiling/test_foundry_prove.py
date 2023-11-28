from __future__ import annotations

import sys
from distutils.dir_util import copy_tree
from typing import TYPE_CHECKING

from pyk.utils import run_process

from kontrol.foundry import Foundry
from kontrol.kompile import foundry_kompile
from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final

    from pyk.testing import Profiler
    from pyk.utils import BugReport


sys.setrecursionlimit(10**7)


FORGE_STD_REF: Final = '75f1746'


def test_foundy_prove(profile: Profiler, use_booster: bool, bug_report: BugReport | None, tmp_path: Path) -> None:
    foundry_root = tmp_path / 'foundry'
    foundry = _forge_build(foundry_root)

    with profile('kompile.prof', sort_keys=('cumtime', 'tottime'), limit=15):
        foundry_kompile(foundry=foundry, includes=())

    with profile('prove.prof', sort_keys=('cumtime', 'tottime'), limit=100):
        foundry_prove(
            foundry,
            tests=[('AssertTest.test_revert_branch', None)],
            prove_options=ProveOptions(
                counterexample_info=True,
                bug_report=bug_report,
            ),
            rpc_options=RPCOptions(
                smt_timeout=300,
                smt_retry_limit=10,
                use_booster=use_booster,
            ),
        )


def _forge_build(target_dir: Path) -> Foundry:
    copy_tree(str(TEST_DATA_DIR / 'foundry'), str(target_dir))
    run_process(['forge', 'install', '--no-git', f'foundry-rs/forge-std@{FORGE_STD_REF}'], cwd=target_dir)
    run_process(['forge', 'build'], cwd=target_dir)
    return Foundry(foundry_root=TEST_DATA_DIR / 'foundry')
