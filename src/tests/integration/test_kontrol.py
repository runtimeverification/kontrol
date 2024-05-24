from __future__ import annotations

import sys
from distutils.dir_util import copy_tree
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server
from pyk.utils import single

from kontrol.foundry import Foundry, init_project
from kontrol.kompile import foundry_kompile
from kontrol.options import BuildOptions, ProveOptions
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR, assert_pass

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport
    from pytest import TempPathFactory


sys.setrecursionlimit(10**7)


@pytest.fixture(scope='module')
def server_end_to_end(foundry_end_to_end: Foundry, no_use_booster: bool) -> Iterator[KoreServer]:
    llvm_definition_dir = foundry_end_to_end.out / 'kompiled' / 'llvm-library' if not no_use_booster else None
    kore_rpc_command = ('kore-rpc-booster',) if not no_use_booster else ('kore-rpc',)

    yield kore_server(
        definition_dir=foundry_end_to_end.kevm.definition_dir,
        llvm_definition_dir=llvm_definition_dir,
        module_name=foundry_end_to_end.kevm.main_module,
        command=kore_rpc_command,
        smt_timeout=500,
        smt_retry_limit=10,
        fallback_on=None,
        interim_simplification=None,
        no_post_exec_simplify=None,
    )


@pytest.fixture(scope='session')
def foundry_end_to_end(foundry_root_dir: Path | None, tmp_path_factory: TempPathFactory, worker_id: str) -> Foundry:
    if worker_id == 'master':
        root_tmp_dir = tmp_path_factory.getbasetemp()
    else:
        root_tmp_dir = tmp_path_factory.getbasetemp().parent

    foundry_root = root_tmp_dir / 'kontrol-test-project'
    with FileLock(str(foundry_root) + '.lock'):
        if not foundry_root.is_dir():
            init_project(project_root=foundry_root, skip_forge=False)
            copy_tree(str(TEST_DATA_DIR / 'src'), str(foundry_root / 'test'))

            foundry_kompile(
                BuildOptions({}),
                foundry=Foundry(foundry_root),
            )

    session_foundry_root = tmp_path_factory.mktemp('kontrol-test-project')
    copy_tree(str(foundry_root), str(session_foundry_root))
    return Foundry(session_foundry_root)


ALL_PROVE_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-all').read_text().splitlines())
SKIPPED_PROVE_TESTS: Final = set((TEST_DATA_DIR / 'end-to-end-prove-skip').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_PROVE_TESTS)
def test_kontrol_end_to_end(
    test_id: str,
    foundry_end_to_end: Foundry,
    update_expected_output: bool,
    no_use_booster: bool,
    bug_report: BugReport | None,
    server_end_to_end: KoreServer,
) -> None:

    if (
        test_id in SKIPPED_PROVE_TESTS
        or (no_use_booster and test_id in SKIPPED_PROVE_TESTS)
        or (update_expected_output)
    ):
        pytest.skip()

    if bug_report is not None:
        server_end_to_end._populate_bug_report(bug_report)

    # When
    prove_res = foundry_prove(
        foundry=foundry_end_to_end,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'bug_report': bug_report,
                'break_on_calls': False,
                'use_gas': False,
                'port': server_end_to_end.port,
            }
        ),
    )

    # Then
    assert_pass(test_id, single(prove_res))
