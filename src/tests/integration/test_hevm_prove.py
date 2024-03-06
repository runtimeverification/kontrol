from __future__ import annotations

import sys
from distutils.dir_util import copy_tree
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server
from pyk.proof import APRProof
from pyk.proof.reachability import APRFailureInfo
from pyk.utils import run_process, single

from kontrol.foundry import Foundry
from kontrol.kompile import foundry_kompile
from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.proof.proof import Proof
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
            )

    session_foundry_root = tmp_path_factory.mktemp('foundry')
    copy_tree(str(foundry_root), str(session_foundry_root))
    return Foundry(session_foundry_root)


def assert_pass(test: str, proof: Proof) -> None:
    if not proof.passed:
        if isinstance(proof, APRProof):
            assert proof.failure_info
            assert isinstance(proof.failure_info, APRFailureInfo)
            pytest.fail('\n'.join(proof.failure_info.print()))
        else:
            pytest.fail()


def assert_fail(test: str, proof: Proof) -> None:
    assert not proof.passed
    if isinstance(proof, APRProof):
        assert proof.failure_info


ALL_HEVM_TESTS_PASSING: Final = (
    'HevmTests.prove_require_assert_true',
    'HevmTests.proveFail_require_assert',
    'HevmTests.prove_revert',
)


@pytest.mark.parametrize('test', ALL_HEVM_TESTS_PASSING)
def test_hevm_prove_passing(
    test: str,
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            counterexample_info=True,
            bug_report=bug_report,
            hevm=True,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    assert_pass(test, single(prove_res))


ALL_HEVM_TESTS_FAILING: Final = (
    'HevmTests.prove_require_assert_false',
    'HevmTests.proveFail_all_branches',
)


@pytest.mark.parametrize('test', ALL_HEVM_TESTS_FAILING)
def test_hevm_prove_failing(
    test: str,
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            counterexample_info=True,
            bug_report=bug_report,
            hevm=True,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    assert_fail(test, single(prove_res))
