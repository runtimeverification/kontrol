from __future__ import annotations

from distutils.dir_util import copy_tree
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server

from kontrol.foundry import Foundry, init_project
from kontrol.kompile import BuildOptions, foundry_kompile

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pytest import TempPathFactory


@pytest.fixture(scope='module')
def server(foundry: Foundry, no_use_booster: bool) -> Iterator[KoreServer]:
    llvm_definition_dir = foundry.out / 'kompiled' / 'llvm-library' if not no_use_booster else None
    kore_rpc_command = ('kore-rpc-booster',) if not no_use_booster else ('kore-rpc',)

    yield kore_server(
        definition_dir=foundry.kevm.definition_dir,
        llvm_definition_dir=llvm_definition_dir,
        module_name=foundry.kevm.main_module,
        command=kore_rpc_command,
        smt_timeout=500,
        smt_retry_limit=10,
        fallback_on=None,
        interim_simplification=None,
        no_post_exec_simplify=None,
    )


TEST_DATA_DIR: Final = (Path(__file__).parent / 'test-data').resolve(strict=True)


@pytest.fixture(scope='session')
def foundry(foundry_root_dir: Path | None, tmp_path_factory: TempPathFactory, worker_id: str) -> Foundry:

    if worker_id == 'master':
        root_tmp_dir = tmp_path_factory.getbasetemp()
    else:
        root_tmp_dir = tmp_path_factory.getbasetemp().parent

    foundry_root = root_tmp_dir / 'kontrol-test-project'
    with FileLock(str(foundry_root) + '.lock'):
        if not foundry_root.is_dir():
            init_project(skip_forge=False, project_root=foundry_root)
            copy_tree(str(TEST_DATA_DIR / 'src'), str(foundry_root / 'src'))

            foundry_kompile(
                BuildOptions({}),
                foundry=Foundry(foundry_root),
            )

    session_foundry_root = tmp_path_factory.mktemp('kontrol-test-project')
    copy_tree(str(foundry_root), str(session_foundry_root))
    return Foundry(session_foundry_root)
