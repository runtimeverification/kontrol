from __future__ import annotations

import sys
import xml.etree.ElementTree as Et
from typing import TYPE_CHECKING

import pytest
from pyk.proof import APRProof
from pyk.proof.reachability import APRFailureInfo
from pyk.utils import single

from kontrol.foundry import (
    Foundry,
    foundry_merge_nodes,
    foundry_refute_node,
    foundry_remove_node,
    foundry_show,
    foundry_split_node,
    foundry_state_diff,
    foundry_step_node,
    foundry_unrefute_node,
)
from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR, assert_or_update_show_output

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.proof.proof import Proof
    from pyk.utils import BugReport
    from pytest import TempPathFactory


sys.setrecursionlimit(10**7)


def test_foundry_kompile(foundry: Foundry, update_expected_output: bool, no_use_booster: bool) -> None:
    if no_use_booster:
        pytest.skip()

    assert_or_update_k_output(
        foundry.main_file,
        TEST_DATA_DIR / 'show/foundry.k.expected',
        update=update_expected_output,
    )
    assert_or_update_k_output(
        foundry.contracts_file,
        TEST_DATA_DIR / 'show/contracts.k.expected',
        update=update_expected_output,
    )


def assert_or_update_k_output(k_file: Path, expected_file: Path, *, update: bool) -> None:
    assert k_file.is_file()

    k_text = k_file.read_text()
    filtered_lines = (line for line in k_text.splitlines() if not line.startswith('    rule  ( #binRuntime ('))

    actual_text = '\n'.join(filtered_lines) + '\n'

    if update:
        expected_file.write_text(actual_text)
    else:
        assert expected_file.is_file()
        expected_text = expected_file.read_text()
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

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_options = ProveOptions(counterexample_info=True, bug_report=bug_report, use_gas=test_id in GAS_TESTS)

    # When
    prove_res = foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=prove_options,
        rpc_options=RPCOptions(port=server.port, smt_timeout=500),
    )

    # Then
    assert_pass(test_id, single(prove_res))

    if test_id not in SHOW_TESTS or no_use_booster:
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
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

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

    if test_id not in SHOW_TESTS:
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
def test_foundry_bmc(
    test_id: str, foundry: Foundry, bug_report: BugReport | None, server: KoreServer, no_use_booster: bool
) -> None:
    if no_use_booster:
        pytest.skip()

    if test_id in SKIPPED_BMC_TESTS:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

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


def test_foundry_merge_nodes(
    foundry: Foundry, bug_report: BugReport | None, server: KoreServer, no_use_booster: bool
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'MergeTest.test_branch_merge(uint256)'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

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


def test_foundry_merge_loop_heads(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'BMCLoopsTest.test_bmc(uint256)'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            max_iterations=20,
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    foundry_merge_nodes(foundry, test=test, node_ids=[15, 16], include_disjunct=True)

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

    show_res = foundry_show(
        foundry,
        test=test,
        to_module=True,
        sort_collections=True,
        omit_unstable_output=True,
        pending=True,
        failing=True,
        failure_info=True,
        counterexample_info=True,
        port=server.port,
    )

    assert_or_update_show_output(
        show_res, TEST_DATA_DIR / 'show/merge-loop-heads.expected', update=update_expected_output
    )


def check_pending(foundry: Foundry, test: str, pending: list[int]) -> None:
    proofs = [foundry.get_optional_proof(pid) for pid in foundry.proof_ids_with_test(test)]
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
    if no_use_booster:
        pytest.skip()

    test_id = 'GasTest.testInfiniteGas()'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

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

    assert_or_update_show_output(
        show_res, TEST_DATA_DIR / 'show/gas-abstraction.expected', update=update_expected_output
    )


def test_foundry_remove_node(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'AssertTest.test_assert_true()'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

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

    proof = foundry.get_optional_proof(single(foundry.proof_ids_with_test(test)))
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
            assert isinstance(proof.failure_info, APRFailureInfo)
            pytest.fail('\n'.join(proof.failure_info.print()))
        else:
            pytest.fail()


def assert_fail(test: str, proof: Proof) -> None:
    assert not proof.passed
    if isinstance(proof, APRProof):
        assert proof.failure_info


def test_foundry_resume_proof(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'AssumeTest.test_assume_false(uint256,uint256)'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

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


ALL_INIT_CODE_TESTS: Final = tuple((TEST_DATA_DIR / 'foundry-init-code').read_text().splitlines())
SKIPPED_INIT_CODE_TESTS: Final = tuple((TEST_DATA_DIR / 'foundry-init-code-skip').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_INIT_CODE_TESTS)
def test_foundry_init_code(
    test_id: str,
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    no_use_booster: bool,
    server: KoreServer,
) -> None:
    if no_use_booster or test_id in SKIPPED_INIT_CODE_TESTS:
        pytest.skip()

    prove_res = foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=ProveOptions(
            run_constructor=True,
            bug_report=bug_report,
            fail_fast=False,
        ),
        rpc_options=RPCOptions(
            smt_timeout=300,
            smt_retry_limit=10,
            use_booster=not no_use_booster,
        ),
    )

    assert_pass(test_id, single(prove_res))


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

    foundry_state_diff(
        'DeploymentState',
        TEST_DATA_DIR / 'accesses.json',
        contract_names=None,
        output_dir_name='src',
        license='UNLICENSED',
        comment_generated_file='// This file was autogenerated by running `kontrol load-state-diff`. Do not edit this file manually.\n',
        foundry=foundry,
    )

    generated_main_file = foundry_root_dir / 'src' / 'DeploymentState.sol'
    generated_code_file = foundry_root_dir / 'src' / 'DeploymentStateCode.sol'

    assert_or_update_show_output(
        generated_main_file.read_text(),
        TEST_DATA_DIR / 'foundry' / 'src' / 'DeploymentState.sol',
        update=update_expected_output,
    )
    assert_or_update_show_output(
        generated_code_file.read_text(),
        TEST_DATA_DIR / 'foundry' / 'src' / 'DeploymentStateCode.sol',
        update=update_expected_output,
    )


def test_foundry_refute_node(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'MergeTest.test_branch_merge'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res_1 = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    # Test initially passes, no pending nodes
    assert_pass(test, single(prove_res_1))
    check_pending(foundry, test, [])

    # Remove successors of nodes 4 and 5
    foundry_remove_node(foundry, test, node=6)
    foundry_remove_node(foundry, test, node=7)

    # Now nodes 4 and 5 are pending
    check_pending(foundry, test, [4, 5])

    # Mark node 4 as refuted
    foundry_refute_node(foundry, test, node=4)

    # Refuted node is not longer pending
    check_pending(foundry, test, [5])

    # Proof will only advance from node 5, since 4 is refuted
    prove_res_2 = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    # Test no longer passing since there are refuted nodes
    assert not single(prove_res_2).passed

    show_res = foundry_show(
        foundry,
        test=test,
        to_module=True,
        sort_collections=True,
        omit_unstable_output=True,
        pending=True,
        failing=True,
        failure_info=True,
        counterexample_info=True,
        port=server.port,
    )

    assert_or_update_show_output(
        show_res, TEST_DATA_DIR / 'show/node-refutation.expected', update=update_expected_output
    )

    check_pending(foundry, test, [])

    # Remove refutation of node 4
    foundry_unrefute_node(foundry, test, node=4)

    check_pending(foundry, test, [4])

    # Execution will continue from node 4
    prove_res_3 = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    # Proof passes again
    assert_pass(test, single(prove_res_3))


def test_foundry_xml_report(
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry,
        tests=[
            ('AssertTest.test_assert_true()', None),
            ('AssertTest.test_assert_false()', None),
            ('AssertNestedTest.test_assert_true_nested()', None),
        ],
        prove_options=ProveOptions(
            counterexample_info=True,
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
        xml_test_report=True,
    )

    tree = Et.parse('kontrol_prove_report.xml')
    testsuites = tree.getroot()
    testsuite = testsuites.find('testsuite[@name="AssertTest"]')
    assert testsuite
    assert testsuite.findall('testcase[@name="test_assert_true()"]')
    failure = testsuite.findall('testcase[@name="test_assert_false()"]')
    assert failure
    assert failure[0].findall('failure')
    testsuite_nested = testsuites.find('testsuite[@name="AssertNestedTest"]')
    assert testsuite_nested
    assert testsuite_nested.findall('testcase[@name="test_assert_true_nested()"]')


def test_foundry_split_node(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'PrankTest.testSymbolicStartPrank'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res_1 = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    assert_pass(test, single(prove_res_1))

    # Remove node with non-deterministic branch
    foundry_remove_node(foundry, test, node=13)

    split_nodes = foundry_split_node(
        foundry,
        test,
        node=12,
        branch_condition='VV0_addr_114b9705 ==Int 491460923342184218035706888008750043977755113263',
    )
    assert split_nodes == [70, 71]

    split_nodes = foundry_split_node(
        foundry,
        test,
        node=71,
        branch_condition='VV0_addr_114b9705 ==Int 645326474426547203313410069153905908525362434349',
    )
    assert split_nodes == [72, 73]

    split_nodes = foundry_split_node(
        foundry,
        test,
        node=73,
        branch_condition='VV0_addr_114b9705 ==Int 728815563385977040452943777879061427756277306518',
    )
    assert split_nodes == [74, 75]

    foundry_refute_node(foundry, test, node=70)
    foundry_refute_node(foundry, test, node=72)
    foundry_refute_node(foundry, test, node=74)

    check_pending(foundry, test, [75])

    prove_res_2 = foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(
            bug_report=bug_report,
        ),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    assert not single(prove_res_2).passed

    show_res = foundry_show(
        foundry,
        test=test,
        to_module=True,
        sort_collections=True,
        omit_unstable_output=True,
        pending=True,
        failing=True,
        failure_info=True,
        counterexample_info=True,
        port=server.port,
    )

    assert_or_update_show_output(show_res, TEST_DATA_DIR / 'show/split-node.expected', update=update_expected_output)
