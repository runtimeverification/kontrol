from __future__ import annotations

import logging
from shutil import copytree
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server
from pyk.utils import run_process_2

from kontrol.foundry import Foundry
from kontrol.kompile import foundry_kompile
from kontrol.options import BuildOptions

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pytest import TempPathFactory


FORGE_STD_REF: Final = '75f1746'
KONTROL_CHEATCODES_REF: Final = 'a5dd4b0'


_LOGGER: Final = logging.getLogger(__name__)


@pytest.fixture(scope='module')
def server(foundry: Foundry) -> Iterator[KoreServer]:
    llvm_definition_dir = foundry.out / 'kompiled' / 'llvm-library'
    kore_rpc_command = ('kore-rpc-booster',)

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


@pytest.fixture(scope='session')
def foundry(foundry_root_dir: Path | None, tmp_path_factory: TempPathFactory, worker_id: str) -> Foundry:
    if foundry_root_dir:
        return Foundry(foundry_root_dir, add_enum_constraints=True)

    if worker_id == 'master':
        root_tmp_dir = tmp_path_factory.getbasetemp()
    else:
        root_tmp_dir = tmp_path_factory.getbasetemp().parent

    foundry_root = root_tmp_dir / 'foundry'
    with FileLock(str(foundry_root) + '.lock'):
        if not foundry_root.is_dir():
            copytree(str(TEST_DATA_DIR / 'foundry'), str(foundry_root), dirs_exist_ok=True)

            run_process_2(['forge', 'install', '--no-git', f'foundry-rs/forge-std@{FORGE_STD_REF}'], cwd=foundry_root)
            run_process_2(
                ['forge', 'install', '--no-git', f'runtimeverification/kontrol-cheatcodes@{KONTROL_CHEATCODES_REF}'],
                cwd=foundry_root,
            )
            run_process_2(['forge', 'build'], cwd=foundry_root)

            try:
                foundry_kompile(
                    BuildOptions(
                        {
                            'includes': (),
                            'requires': [
                                str(TEST_DATA_DIR / 'lemmas.k'),
                                str(TEST_DATA_DIR / 'cse-lemmas.k'),
                                str(TEST_DATA_DIR / 'pausability-lemmas.k'),
                                str(TEST_DATA_DIR / 'symbolic-bytes-lemmas.k'),
                            ],
                            'imports': [
                                'LoopsTest:SUM-TO-N-INVARIANT',
                                'ArithmeticCallTest:CSE-LEMMAS',
                                'CSETest:CSE-LEMMAS',
                                'PortalTest:PAUSABILITY-LEMMAS',
                                'ImmutableVarsTest:SYMBOLIC-BYTES-LEMMAS',
                            ],
                            'enum_constraints': True,
                            'metadata': False,
                        }
                    ),
                    foundry=Foundry(foundry_root, add_enum_constraints=True),
                )
            except CalledProcessError as e:
                _LOGGER.warning(e)
                _LOGGER.warning(e.stdout)
                _LOGGER.warning(e.stderr)
                raise e

    session_foundry_root = tmp_path_factory.mktemp('foundry')
    copytree(str(foundry_root), str(session_foundry_root), dirs_exist_ok=True)
    return Foundry(session_foundry_root, add_enum_constraints=True)
