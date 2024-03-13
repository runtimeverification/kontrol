from __future__ import annotations

import sys
from distutils.dir_util import copy_tree
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server
from pyk.utils import run_process

from kontrol.foundry import Foundry, foundry_show
from kontrol.kompile import foundry_kompile
from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR, assert_or_update_show_output

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport
    from pytest import TempPathFactory


FORGE_STD_REF: Final = '75f1746'


sys.setrecursionlimit(10**7)


@pytest.fixture(scope='module')
def server(foundry: Foundry, no_use_booster: bool) -> Iterator[KoreServer]:
    llvm_definition_dir = foundry.out / 'kompiled' / 'llvm-library' if not no_use_booster else None
    kore_rpc_command = ('kore-rpc-booster',) if not no_use_booster else ('kore-rpc',)

    yield kore_server(
        definition_dir=foundry.kevm.definition_dir,
        llvm_definition_dir=llvm_definition_dir,
        module_name=foundry.kevm.main_module,
        command=kore_rpc_command,
        smt_timeout=300,
        smt_retry_limit=10,
        fallback_on=None,
        interim_simplification=None,
        no_post_exec_simplify=None,
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
            run_process(['forge', 'build'], cwd=foundry_root)

            foundry_kompile(
                foundry=Foundry(foundry_root),
                includes=(),
                requires=[str(TEST_DATA_DIR / 'lemmas.k'), str(TEST_DATA_DIR / 'cse-lemmas.k')],
                imports=['LoopsTest:SUM-TO-N-INVARIANT', 'CSETest:CSE-LEMMAS'],
            )

    session_foundry_root = tmp_path_factory.mktemp('foundry')
    copy_tree(str(foundry_root), str(session_foundry_root))
    return Foundry(session_foundry_root)


ALL_DEPENDENCY_TESTS: Final = tuple((TEST_DATA_DIR / 'foundry-dependency-all').read_text().splitlines())
SKIPPED_DEPENDENCY_TESTS: Final = set((TEST_DATA_DIR / 'foundry-dependency-skip').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_DEPENDENCY_TESTS)
def test_foundry_dependency_automated(
    test_id: str,
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    update_expected_output: bool,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if test_id in SKIPPED_DEPENDENCY_TESTS:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    # Execution without CSE
    prove_options = ProveOptions(
        max_iterations=50,
        bug_report=bug_report,
        cse=True,
        fail_fast=False,
        workers=2,
    )

    foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=prove_options,
        rpc_options=RPCOptions(port=server.port, smt_timeout=500),
    )

    show_res = foundry_show(
        foundry,
        test=test_id,
        to_module=False,
        sort_collections=True,
        omit_unstable_output=True,
        pending=False,
        failing=False,
        failure_info=False,
        counterexample_info=False,
        port=server.port,
    )

    assert_or_update_show_output(
        show_res, TEST_DATA_DIR / f'show/{test_id}.no-cse.expected', update=update_expected_output
    )

    # Execution with CSE
    cse_prove_options = ProveOptions(
        max_iterations=50,
        bug_report=bug_report,
        cse=True,
        fail_fast=False,
        workers=2,
    )

    foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=cse_prove_options,
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    cse_show_res = foundry_show(
        foundry,
        test=test_id,
        to_module=False,
        sort_collections=True,
        omit_unstable_output=True,
        pending=False,
        failing=False,
        failure_info=False,
        counterexample_info=False,
        port=server.port,
    )

    assert_or_update_show_output(
        cse_show_res, TEST_DATA_DIR / f'show/{test_id}.cse.expected', update=update_expected_output
    )
