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
            copytree(str(TEST_DATA_DIR / 'src'), str(foundry_root / 'src'), dirs_exist_ok=True)
            copytree(str(TEST_DATA_DIR / 'test'), str(foundry_root / 'test'), dirs_exist_ok=True)
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


def test_kontrol_setup_storage(foundry_end_to_end: Foundry, update_expected_output: bool) -> None:
    """Test the setup-storage command with both storage constants and setup contract generation."""

    options = SetupStorageOptions(
        {
            'contract_names': ['src%SimpleStorage'],
            'solidity_version': '0.8.26',
            'output_file': None,
            'foundry_root': foundry_end_to_end._root,
            'enum_constraints': False,
            'log_level': 'INFO',
            'generate_setup_contracts': True,
        }
    )

    foundry_storage_generation(foundry_end_to_end, options)

    # Check that storage constants file was created
    storage_file = foundry_end_to_end._root / 'test' / 'kontrol' / 'storage' / 'SimpleStorageStorageConstants.sol'
    assert storage_file.exists(), f'SimpleStorage constants file not created: {storage_file}'

    # Check storage constants content and update expected output
    storage_content = storage_file.read_text()
    assert_or_update_show_output(
        storage_content,
        TEST_DATA_DIR / 'show' / 'SimpleStorageStorageConstants.expected',
        update=update_expected_output,
    )

    # Check that setup contract file was created
    setup_file = foundry_end_to_end._root / 'test' / 'kontrol' / 'setup' / 'SimpleStorageStorageSetup.sol'
    assert setup_file.exists(), f'SimpleStorage setup file not created: {setup_file}'

    # Check setup contract content and update expected output
    setup_content = setup_file.read_text()
    assert_or_update_show_output(
        setup_content,
        TEST_DATA_DIR / 'show' / 'SimpleStorageStorageSetup.expected',
        update=update_expected_output,
    )


def test_kontrol_counterexample_generation(foundry_end_to_end: Foundry, update_expected_output: bool) -> None:
    """Test counterexample generation for a failing proof."""

    # Run kontrol prove with --generate-counterexample on a test that will fail
    prove_options = ProveOptions(
        {
            'tests': ['UnitTest.test_counterexample'],
            'workers': 1,
            'foundry_root': foundry_end_to_end._root,
            'max_depth': 10000,
            'max_iterations': 10000,
            'reinit': False,
            'bug_report': None,
            'xml_test_report': False,
            'failure_info': False,
            'auto_abstract_gas': False,
            'run_constructor': False,
            'symbolic_caller': False,
            'generate_counterexample': True,  # Enable counterexample generation
        }
    )

    # Run the prove command (this should fail and generate a counterexample)
    foundry_prove(foundry_end_to_end, prove_options)

    # Check that the counterexample file was created in the same directory as the original test
    counterexample_file = foundry_end_to_end._root / 'test' / 'UnitTestCounterexampleTest.t.sol'
    assert counterexample_file.exists(), f'Counterexample file not created: {counterexample_file}'

    # Check counterexample content and update expected output
    counterexample_content = counterexample_file.read_text()
    assert_or_update_show_output(
        counterexample_content,
        TEST_DATA_DIR / 'show' / 'UnitTestCounterexampleTest.expected',
        update=update_expected_output,
    )
