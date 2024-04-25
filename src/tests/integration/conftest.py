from __future__ import annotations

from distutils.dir_util import copy_tree
from functools import partial
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server
from pyk.utils import run_process

from kontrol.foundry import Foundry
from kontrol.kompile import BuildOptions, foundry_kompile

from .utils import TEST_DATA_DIR, gen_bin_runtime

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pytest import TempPathFactory


FORGE_STD_REF: Final = '75f1746'


@pytest.fixture
def bin_runtime(tmp_path: Path) -> Callable[[Path], tuple[Path, str]]:
    return partial(gen_bin_runtime, output_dir=tmp_path)


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
        haskell_threads=3,
    )


@pytest.fixture(scope='session')
def foundry(foundry_root_dir: Path | None, tmp_path_factory: TempPathFactory, worker_id: str) -> Foundry:
    if foundry_root_dir:
        return Foundry(foundry_root_dir)

    if worker_id == 'master':
        root_tmp_dir = tmp_path_factory.getbasetemp()
    else:
        root_tmp_dir = tmp_path_factory.getbasetemp().parent

    foundry_root = root_tmp_dir / 'foundry'
    with FileLock(str(foundry_root) + '.lock'):
        if not foundry_root.is_dir():
            copy_tree(str(TEST_DATA_DIR / 'foundry'), str(foundry_root))

            run_process(['forge', 'install', '--no-git', f'foundry-rs/forge-std@{FORGE_STD_REF}'], cwd=foundry_root)
            run_process(['forge', 'install', '--no-git', 'runtimeverification/kontrol-cheatcodes'], cwd=foundry_root)
            run_process(['forge', 'build'], cwd=foundry_root)

            foundry_kompile(
                BuildOptions(
                    {
                        'includes': (),
                        'requires': [
                            str(TEST_DATA_DIR / 'lemmas.k'),
                            str(TEST_DATA_DIR / 'cse-lemmas.k'),
                            str(TEST_DATA_DIR / 'pausability-lemmas.k'),
                        ],
                        'imports': [
                            'LoopsTest:SUM-TO-N-INVARIANT',
                            'ArithmeticCallTest:CSE-LEMMAS',
                            'CSETest:CSE-LEMMAS',
                            'PortalTest:PAUSABILITY-LEMMAS',
                        ],
                    }
                ),
                foundry=Foundry(foundry_root),
            )

    session_foundry_root = tmp_path_factory.mktemp('foundry')
    copy_tree(str(foundry_root), str(session_foundry_root))
    return Foundry(session_foundry_root)
