from __future__ import annotations

import sys
from os import getenv
from shutil import copytree
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server
from pyk.utils import single

from kontrol.foundry import Foundry, foundry_show, init_project
from kontrol.kompile import foundry_kompile
from kontrol.options import BuildOptions, ProveOptions, ShowOptions
from kontrol.prove import foundry_prove
from kontrol.utils import append_to_file, foundry_toml_cancun_schedule

from .utils import TEST_DATA_DIR, assert_or_update_show_output, assert_pass

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
            copytree(str(TEST_DATA_DIR / 'src'), str(foundry_root / 'test'), dirs_exist_ok=True)
            append_to_file(foundry_root / 'foundry.toml', foundry_toml_cancun_schedule())

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

    session_foundry_root = tmp_path_factory.mktemp('kontrol-test-project')
    copytree(str(foundry_root), str(session_foundry_root), dirs_exist_ok=True)
    return Foundry(session_foundry_root)


ALL_PROVE_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-all').read_text().splitlines())
ALL_FORKED_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-forked').read_text().splitlines())
SKIPPED_PROVE_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-skip').read_text().splitlines())
SHOW_TESTS: Final = tuple((TEST_DATA_DIR / 'end-to-end-prove-show').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_PROVE_TESTS)
def test_kontrol_end_to_end(
    test_id: str,
    foundry_end_to_end: Foundry,
    update_expected_output: bool,
    no_use_booster: bool,
    bug_report: BugReport | None,
    server_end_to_end: KoreServer,
    force_sequential: bool,
) -> None:

    if (
        test_id in SKIPPED_PROVE_TESTS
        or (no_use_booster and test_id in SKIPPED_PROVE_TESTS)
        or (update_expected_output and test_id not in SHOW_TESTS)
    ):
        pytest.skip()

    if bug_report is not None:
        server_end_to_end._populate_bug_report(bug_report)

    options = ProveOptions(
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
    )
    fork_options = ProveOptions(
        {
            'tests': [(test_id, None)],
            'bug_report': bug_report,
            'break_on_calls': False,
            'usegas': False,
            'port': server_end_to_end.port,
            'force_sequential': force_sequential,
            'schedule': 'CANCUN',
            'stack_checks': False,
            'fork_url': getenv('WEB3_PROVIDER_KEY'),
            'fork_block_number': 131674109,
        }
    )
    print('web3 key available: ', getenv('WEB3_PROVIDER_KEY') is not None)
    # When
    prove_res = foundry_prove(
        foundry=foundry_end_to_end, options=fork_options if test_id in ALL_FORKED_TESTS else options
    )

    # Then

    if test_id not in SHOW_TESTS or no_use_booster:
        assert_pass(test_id, single(prove_res))
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
