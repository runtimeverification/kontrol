from __future__ import annotations

import sys
from distutils.dir_util import copy_tree
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.utils import single

from kontrol.foundry import Foundry, init_project
from kontrol.kompile import BuildOptions, foundry_kompile
from kontrol.prove import ProveOptions, foundry_prove

from .utils import TEST_DATA_DIR, assert_pass

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport
    from pytest import TempPathFactory


sys.setrecursionlimit(10**7)

ALL_PROVE_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-all').read_text().splitlines())


@pytest.fixture(scope='session')
def foundry_project(foundry_root_dir: Path | None, tmp_path_factory: TempPathFactory, worker_id: str) -> Foundry:
    if foundry_root_dir:
        return Foundry(foundry_root_dir)

    if worker_id == 'master':
        root_tmp_dir = tmp_path_factory.getbasetemp()
    else:
        root_tmp_dir = tmp_path_factory.getbasetemp().parent

    foundry_root = root_tmp_dir / 'kontrol-test-project'
    with FileLock(str(foundry_root) + '.lock'):
        if not foundry_root.is_dir():
            init_project(project_root=foundry_root, skip_forge=False)
            copy_tree(str(TEST_DATA_DIR / 'src'), str(foundry_root / 'src'))

            foundry_kompile(
                BuildOptions({}),
                foundry=Foundry(foundry_root),
            )

    session_foundry_root = tmp_path_factory.mktemp('kontrol-test-project')
    copy_tree(str(foundry_root), str(session_foundry_root))
    return Foundry(session_foundry_root)


@pytest.mark.parametrize('test_id', ALL_PROVE_TESTS)
def test_kontrol_end_to_end(
    test_id: str,
    foundry_project: Foundry,
    update_expected_output: bool,
    no_use_booster: bool,
    bug_report: BugReport | None,
    server: KoreServer,
) -> None:

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    # When
    prove_res = foundry_prove(
        foundry=foundry_project,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'use_gas': False,
                'port': server.port,
            }
        ),
    )

    # Then
    assert_pass(test_id, single(prove_res))
