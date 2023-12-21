from __future__ import annotations

import sys
from distutils.dir_util import copy_tree
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock
from pyk.kore.rpc import kore_server
from pyk.proof import APRProof
from pyk.utils import run_process, single

from kontrol.foundry import (
    Foundry,
    foundry_merge_nodes,
    foundry_remove_node,
    foundry_show,
    foundry_step_node,
    foundry_summary,
)
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
                requires=[str(TEST_DATA_DIR / 'lemmas.k')],
                imports=['LoopsTest:SUM-TO-N-INVARIANT'],
            )

    session_foundry_root = tmp_path_factory.mktemp('foundry')
    copy_tree(str(foundry_root), str(session_foundry_root))
    return Foundry(session_foundry_root)


def test_foundry_kompile(foundry: Foundry, update_expected_output: bool, no_use_booster: bool) -> None:
    if not no_use_booster:
        return
    # Then
    assert_or_update_k_output(
        foundry.main_file,
        TEST_DATA_DIR / 'foundry.k.expected',
        update=update_expected_output,
    )
    assert_or_update_k_output(
        foundry.contracts_file,
        TEST_DATA_DIR / 'contracts.k.expected',
        update=update_expected_output,
    )


def assert_or_update_k_output(k_file: Path, expected_file: Path, *, update: bool) -> None:
    assert k_file.is_file()
    assert expected_file.is_file()

    k_text = k_file.read_text()
    filtered_lines = (line for line in k_text.splitlines() if not line.startswith('    rule  ( #binRuntime ('))

    actual_text = '\n'.join(filtered_lines) + '\n'
    expected_text = expected_file.read_text()

    if update:
        expected_file.write_text(actual_text)
    else:
        assert actual_text == expected_text


ALL_PROVE_TESTS: Final = tuple((TEST_DATA_DIR / 'foundry-prove-all').read_text().splitlines())
SKIPPED_PROVE_TESTS: Final = set((TEST_DATA_DIR / 'foundry-prove-skip').read_text().splitlines())
SKIPPED_LEGACY_TESTS: Final = set((TEST_DATA_DIR / 'foundry-prove-skip-legacy').read_text().splitlines())
GAS_TESTS: Final = set((TEST_DATA_DIR / 'foundry-prove-with-gas').read_text().splitlines())

SHOW_TESTS = set((TEST_DATA_DIR / 'foundry-show').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_PROVE_TESTS)
def test_foundry_prove(
    test_id: str,
    foundry: Foundry,
    update_expected_output: bool,
    no_use_booster: bool,
    bug_report: BugReport | None,
    server: KoreServer,
) -> None:
    if (
        test_id in SKIPPED_PROVE_TESTS
        or (no_use_booster and test_id in SKIPPED_LEGACY_TESTS)
        or (update_expected_output and not test_id in SHOW_TESTS)
    ):
        pytest.skip()

    prove_options = ProveOptions(counterexample_info=True, bug_report=bug_report, use_gas=test_id in GAS_TESTS)

    # When
    prove_res = single(
        foundry_prove(
            foundry,
            tests=[(test_id, None)],
            prove_options=prove_options,
            rpc_options=RPCOptions(
                port=server.port,
            ),
        )
    )

    # Then
    assert_pass(test_id, prove_res)

    if test_id not in SHOW_TESTS or not no_use_booster:
        return

    # And when
    show_res = foundry_show(
        foundry,
        test=test_id,
        to_module=True,
        sort_collections=True,
        omit_unstable_output=True,
        pending=True,
        failing=True,
        failure_info=True,
        counterexample_info=True,
        port=server.port,
    )

    # Then
    assert_or_update_show_output(show_res, TEST_DATA_DIR / f'show/{test_id}.expected', update=update_expected_output)


FAIL_TESTS: Final = tuple((TEST_DATA_DIR / 'foundry-fail').read_text().splitlines())


@pytest.mark.parametrize('test_id', FAIL_TESTS)
def test_foundry_fail(
    test_id: str,
    foundry: Foundry,
    update_expected_output: bool,
    no_use_booster: bool,
    bug_report: BugReport | None,
    server: KoreServer,
) -> None:
    # When
    prove_res = foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=ProveOptions(
            counterexample_info=True,
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    # Then
    assert_fail(test_id, single(prove_res))

    if test_id not in SHOW_TESTS or not no_use_booster:
        return

    # And when
    show_res = foundry_show(
        foundry,
        test=test_id,
        to_module=True,
        sort_collections=True,
        omit_unstable_output=True,
        pending=True,
        failing=True,
        failure_info=True,
        counterexample_info=True,
        port=server.port,
    )

    # Then
    assert_or_update_show_output(show_res, TEST_DATA_DIR / f'show/{test_id}.expected', update=update_expected_output)


ALL_BMC_TESTS: Final = tuple((TEST_DATA_DIR / 'foundry-bmc-all').read_text().splitlines())
SKIPPED_BMC_TESTS: Final = set((TEST_DATA_DIR / 'foundry-bmc-skip').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_BMC_TESTS)
def test_foundry_bmc(test_id: str, foundry: Foundry, bug_report: BugReport | None, server: KoreServer) -> None:
    if test_id in SKIPPED_BMC_TESTS:
        pytest.skip()

    # When
    prove_res = foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=ProveOptions(
            bmc_depth=3,
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    # Then
    assert_pass(test_id, single(prove_res))


def test_foundry_merge_nodes(foundry: Foundry, bug_report: BugReport | None, server: KoreServer) -> None:
    test = 'MergeTest.test_branch_merge(uint256)'

    foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            max_iterations=2,
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    check_pending(foundry, test, [4, 5])

    foundry_step_node(
        foundry,
        test,
        node=4,
        depth=49,
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )
    foundry_step_node(
        foundry,
        test,
        node=5,
        depth=50,
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )
    check_pending(foundry, test, [6, 7])

    foundry_merge_nodes(foundry, test=test, node_ids=[6, 7], include_disjunct=True)

    check_pending(foundry, test, [8])

    prove_res = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )
    assert_pass(test, single(prove_res))


def check_pending(foundry: Foundry, test: str, pending: list[int]) -> None:
    proofs = foundry.proofs_with_test(test)
    apr_proofs: list[APRProof] = [proof for proof in proofs if type(proof) is APRProof]
    proof = single(apr_proofs)
    assert [node.id for node in proof.pending] == pending


def test_foundry_auto_abstraction(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    test_id = 'GasTest.testInfiniteGas()'

    foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=ProveOptions(
            auto_abstract_gas=True,
            bug_report=bug_report,
            use_gas=True,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    if not no_use_booster:
        return

    show_res = foundry_show(
        foundry,
        test=test_id,
        to_module=True,
        minimize=False,
        sort_collections=True,
        omit_unstable_output=True,
        pending=True,
        failing=True,
        failure_info=True,
        port=server.port,
    )

    assert_or_update_show_output(show_res, TEST_DATA_DIR / 'gas-abstraction.expected', update=update_expected_output)


def test_foundry_remove_node(
    foundry: Foundry, update_expected_output: bool, bug_report: BugReport | None, server: KoreServer
) -> None:
    test = 'AssertTest.test_assert_true()'

    prove_res = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )
    assert_pass(test, single(prove_res))

    foundry_remove_node(
        foundry,
        test=test,
        node=4,
    )

    proof = single(foundry.proofs_with_test(test))
    assert type(proof) is APRProof
    assert proof.pending

    prove_res = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )
    assert_pass(test, single(prove_res))


def assert_pass(test: str, proof: Proof) -> None:
    if not proof.passed:
        if isinstance(proof, APRProof):
            assert proof.failure_info
            pytest.fail('\n'.join(proof.failure_info.print()))
        else:
            pytest.fail()


def assert_fail(test: str, proof: Proof) -> None:
    assert not proof.passed
    if isinstance(proof, APRProof):
        assert proof.failure_info


def assert_or_update_show_output(show_res: str, expected_file: Path, *, update: bool) -> None:
    assert expected_file.is_file()

    filtered_lines = (
        line
        for line in show_res.splitlines()
        if not line.startswith(
            (
                '    src: ',
                '│   src: ',
                '┃  │   src: ',
                '   │   src: ',
                'module',
            )
        )
    )
    actual_text = '\n'.join(filtered_lines) + '\n'
    expected_text = expected_file.read_text()

    if update:
        expected_file.write_text(actual_text)
    else:
        assert actual_text == expected_text


def test_foundry_resume_proof(
    foundry: Foundry, update_expected_output: bool, bug_report: BugReport | None, server: KoreServer
) -> None:
    test = 'AssumeTest.test_assume_false(uint256,uint256)'

    prove_res = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            auto_abstract_gas=True,
            max_iterations=4,
            reinit=True,
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    proof = single(prove_res)
    assert isinstance(proof, APRProof)
    assert proof.pending

    prove_res = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            auto_abstract_gas=True,
            max_iterations=10,
            reinit=False,
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    assert_fail(test, single(prove_res))


ALL_INIT_CODE_TESTS: Final = ('InitCodeTest.test_init()', 'InitCodeTest.testFail_init()')


@pytest.mark.parametrize('test', ALL_INIT_CODE_TESTS)
def test_foundry_init_code(test: str, foundry: Foundry, bug_report: BugReport | None, no_use_booster: bool) -> None:
    # When
    prove_res = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            run_constructor=True,
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            smt_timeout=300,
            smt_retry_limit=10,
            use_booster=not no_use_booster,
        ),
    )

    # Then
    assert_pass(test, single(prove_res))


def test_foundry_duplicate_contract_names(foundry: Foundry) -> None:
    assert 'src%duplicates%1%DuplicateName' in foundry.contracts.keys()
    assert 'src%duplicates%2%DuplicateName' in foundry.contracts.keys()


def test_deployment_summary(
    foundry_root_dir: Path | None,
    server: KoreServer,
    bug_report: BugReport,
    worker_id: str,
    tmp_path_factory: TempPathFactory,
    update_expected_output: bool,
) -> None:
    if not foundry_root_dir:
        if worker_id == 'master':
            root_tmp_dir = tmp_path_factory.getbasetemp()
        else:
            root_tmp_dir = tmp_path_factory.getbasetemp().parent

        foundry_root_dir = root_tmp_dir / 'foundry'
    foundry = Foundry(foundry_root=foundry_root_dir)

    foundry_summary(
        'DeploymentSummary',
        TEST_DATA_DIR / 'accesses.json',
        contract_names=None,
        output_dir_name='src',
        foundry=foundry,
    )

    generated_main_file = foundry_root_dir / 'src' / 'DeploymentSummary.sol'
    generated_code_file = foundry_root_dir / 'src' / 'DeploymentSummaryCode.sol'

    assert_or_update_show_output(
        generated_main_file.read_text(),
        TEST_DATA_DIR / 'foundry' / 'src' / 'DeploymentSummary.sol',
        update=update_expected_output,
    )
    assert_or_update_show_output(
        generated_code_file.read_text(),
        TEST_DATA_DIR / 'foundry' / 'src' / 'DeploymentSummaryCode.sol',
        update=update_expected_output,
    )
