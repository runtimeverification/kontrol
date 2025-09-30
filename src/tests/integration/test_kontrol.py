from __future__ import annotations

import logging
import sys
from shutil import copytree
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server
from pyk.utils import single

from kontrol.display import foundry_show
from kontrol.foundry import Foundry, foundry_storage_generation, init_project
from kontrol.kompile import foundry_kompile
from kontrol.options import BuildOptions, ProveOptions, SetupStorageOptions, ShowOptions
from kontrol.prove import foundry_prove
from kontrol.utils import append_to_file, foundry_toml_use_optimizer

from .utils import TEST_DATA_DIR, assert_or_update_show_output, assert_pass

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport
    from pytest import TempPathFactory


sys.setrecursionlimit(10**7)


_LOGGER: Final = logging.getLogger(__name__)


@pytest.fixture(scope='module')
def server_end_to_end(foundry_end_to_end: Foundry) -> Iterator[KoreServer]:
    llvm_definition_dir = foundry_end_to_end.out / 'kompiled' / 'llvm-library'
    kore_rpc_command = ('kore-rpc-booster',)

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
            copytree(str(TEST_DATA_DIR / 'src'), str(foundry_root / 'test'), dirs_exist_ok=True)
            append_to_file(foundry_root / 'foundry.toml', foundry_toml_use_optimizer())

            try:
                foundry_kompile(
                    BuildOptions(
                        {
                            'require': str(foundry_root / 'lemmas.k'),
                            'module-import': 'TestBase:KONTROL-LEMMAS',
                            'metadata': False,
                            'auxiliary_lemmas': True,
                        }
                    ),
                    foundry=Foundry(foundry_root),
                )
            except CalledProcessError as e:
                _LOGGER.warning(e)
                _LOGGER.warning(e.stdout)
                _LOGGER.warning(e.stderr)
                raise

    session_foundry_root = tmp_path_factory.mktemp('kontrol-test-project')
    copytree(str(foundry_root), str(session_foundry_root), dirs_exist_ok=True)
    return Foundry(session_foundry_root)


ALL_PROVE_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-all').read_text().splitlines())
SKIPPED_PROVE_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-skip').read_text().splitlines())
SHOW_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-show').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_PROVE_TESTS)
def test_kontrol_end_to_end(
    test_id: str,
    foundry_end_to_end: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server_end_to_end: KoreServer,
    force_sequential: bool,
) -> None:

    if test_id in SKIPPED_PROVE_TESTS or (update_expected_output and test_id not in SHOW_TESTS):
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
                'usegas': False,
                'port': server_end_to_end.port,
                'force_sequential': force_sequential,
                'schedule': 'CANCUN',
                'stack_checks': False,
            }
        ),
    )

    # Then
    assert_pass(test_id, single(prove_res))

    if test_id not in SHOW_TESTS:
        return

    # And when
    show_res = foundry_show(
        foundry=foundry_end_to_end,
        options=ShowOptions(
            {
                'test': test_id,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server_end_to_end.port,
            }
        ),
    )

    # Then
    assert_or_update_show_output(show_res, TEST_DATA_DIR / f'show/{test_id}.expected', update=update_expected_output)


def test_setup_storage_end_to_end(
    foundry_end_to_end: Foundry, 
    update_expected_output: bool
) -> None:
    """Test the setup-storage command as part of end-to-end tests."""

    options = SetupStorageOptions(
        {
            'contract_names': ['src%Token'],
            'solidity_version': '0.8.26',
            'output_file': None,
            'foundry_root': foundry_end_to_end._root,
            'enum_constraints': False,
            'log_level': 'INFO',
        }
    )

    foundry_storage_generation(foundry_end_to_end, options)

    # Check that output file was created
    token_file = foundry_end_to_end._root / 'test' / 'kontrol' / 'storage' / 'TokenStorageConstants.sol'

    assert token_file.exists(), f'Token file not created: {token_file}'

    # Check Token content and update expected output
    token_content = token_file.read_text()
    assert_or_update_show_output(token_content, TEST_DATA_DIR / 'show' / 'TokenStorageConstants.expected', update=update_expected_output)
