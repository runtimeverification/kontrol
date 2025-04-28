from __future__ import annotations

import sys
import xml.etree.ElementTree as Et
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pyk.proof import APRProof
from pyk.proof.proof import Proof
from pyk.utils import single

from kontrol.display import foundry_show
from kontrol.foundry import (
    Foundry,
    foundry_merge_nodes,
    foundry_minimize_proof,
    foundry_refute_node,
    foundry_remove_node,
    foundry_split_node,
    foundry_state_load,
    foundry_step_node,
    foundry_unrefute_node,
)
from kontrol.options import (
    LoadStateOptions,
    MergeNodesOptions,
    MinimizeProofOptions,
    ProveOptions,
    RefuteNodeOptions,
    RemoveNodeOptions,
    ShowOptions,
    SplitNodeOptions,
    StepNodeOptions,
    UnrefuteNodeOptions,
)
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR, assert_fail, assert_or_update_show_output, assert_pass

if TYPE_CHECKING:
    from typing import Final

    from pyk.kore.rpc import KoreServer
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
    force_sequential: bool,
) -> None:
    if (
        test_id in SKIPPED_PROVE_TESTS
        or (no_use_booster and test_id in SKIPPED_LEGACY_TESTS)
        or (update_expected_output and not test_id in SHOW_TESTS)
    ):
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    # When
    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'bug_report': bug_report,
                'break_on_calls': test_id in SHOW_TESTS,
                'usegas': test_id in GAS_TESTS,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    # Then
    assert_pass(test_id, single(prove_res))

    if test_id not in SHOW_TESTS or no_use_booster:
        return

    # And when
    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test_id,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
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
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'bug_report': bug_report,
                'break_on_calls': test_id in SHOW_TESTS,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    # then
    assert_fail(test_id, single(prove_res))

    if test_id not in SHOW_TESTS:
        return

    # and when
    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test_id,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
    )

    # then
    assert_or_update_show_output(show_res, TEST_DATA_DIR / f'show/{test_id}.expected', update=update_expected_output)


def test_constructor_with_symbolic_args(
    foundry: Foundry,
    update_expected_output: bool,
    no_use_booster: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    test_id = 'ImmutableVarsTest.test_run_deployment(uint256)'
    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'break_on_load_program': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    # then
    assert_fail(test_id, single(prove_res))

    if test_id not in SHOW_TESTS:
        return

    # and when
    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test_id,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
    )

    # then
    assert_or_update_show_output(show_res, TEST_DATA_DIR / f'show/{test_id}.expected', update=update_expected_output)


all_bmc_tests: Final = tuple((TEST_DATA_DIR / 'foundry-bmc-all').read_text().splitlines())
skipped_bmc_tests: Final = set((TEST_DATA_DIR / 'foundry-bmc-skip').read_text().splitlines())


@pytest.mark.parametrize('test_id', all_bmc_tests)
def test_foundry_bmc(
    test_id: str,
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if test_id in skipped_bmc_tests:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    # when
    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'bmc_depth': 3,
                'bug_report': bug_report,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    # Then
    assert_pass(test_id, single(prove_res))

    if test_id not in SHOW_TESTS:
        return

    # And when
    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test_id,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
    )

    # Then
    assert_or_update_show_output(show_res, TEST_DATA_DIR / f'show/{test_id}.expected', update=update_expected_output)


MINIMIZE_TESTS = tuple((TEST_DATA_DIR / 'foundry-minimize').read_text().splitlines())
MINIMIZE_MERGE_TESTS = tuple((TEST_DATA_DIR / 'foundry-minimize-merge').read_text().splitlines())


@pytest.mark.parametrize('test_id', MINIMIZE_TESTS)
def test_foundry_minimize_proof(
    test_id: str,
    foundry: Foundry,
    update_expected_output: bool,
    no_use_booster: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    force_sequential: bool,
) -> None:
    merge = test_id in MINIMIZE_MERGE_TESTS

    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    options = ProveOptions(
        {
            'tests': [(test_id, None)],
            'break_on_calls': True,
            'reinit': True,
            'bug_report': bug_report,
            'port': server.port,
            'force_sequential': force_sequential,
        }
    )

    # When
    foundry_prove(foundry=foundry, options=options)

    foundry_minimize_proof(foundry, options=MinimizeProofOptions({'test': test_id, 'merge': merge}))

    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test_id,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
    )

    # Then
    assert_or_update_show_output(
        show_res, TEST_DATA_DIR / f'show/minimized/{test_id}.expected', update=update_expected_output
    )


def test_foundry_merge_nodes(
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'MergeTest.test_branch_merge(uint256)'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'max_iterations': 2,
                'bug_report': bug_report,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    check_pending(foundry, test, [4, 5])

    foundry_step_node(
        foundry,
        options=StepNodeOptions(
            {
                'test': test,
                'node': 4,
                'depth': 49,
                'port': server.port,
            }
        ),
    )
    foundry_step_node(
        foundry,
        options=StepNodeOptions(
            {
                'test': test,
                'node': 5,
                'depth': 50,
                'port': server.port,
            }
        ),
    )
    check_pending(foundry, test, [6, 7])

    foundry_merge_nodes(foundry, MergeNodesOptions({'test': test, 'nodes': [6, 7], 'include_disjunct': True}))

    check_pending(foundry, test, [8])

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )
    assert_pass(test, single(prove_res))


def test_foundry_show_with_hex_encoding(
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
    foundry_root_dir: Path | None,
    worker_id: str,
    tmp_path_factory: TempPathFactory,
) -> None:

    if not foundry_root_dir:
        if worker_id == 'master':
            root_tmp_dir = tmp_path_factory.getbasetemp()
        else:
            root_tmp_dir = tmp_path_factory.getbasetemp().parent

        foundry_root_dir = root_tmp_dir / 'foundry'
    foundry = Foundry(foundry_root=foundry_root_dir, use_hex_encoding=True)

    if no_use_booster:
        pytest.skip()

    test = 'CounterTest.testIncrement()'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test,
                'port': server.port,
                'nodes': [1, 3, 4, 5, 6, 7, 2],
            }
        ),
    )


def test_foundry_merge_loop_heads(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'BMCLoopsTest.test_bmc(uint256)'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'max_iterations': 15,
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    check_pending(foundry, test, [17, 18, 19])

    foundry_merge_nodes(foundry, MergeNodesOptions({'test': test, 'nodes': [4, 9, 15], 'include_disjunct': True}))

    check_pending(foundry, test, [19, 20])

    foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'max_iterations': 2,
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
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
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test_id = 'GasTest.testInfiniteGas()'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'auto_abstract_gas': True,
                'bug_report': bug_report,
                'break_on_calls': True,
                'usegas': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test_id,
                'to_module': True,
                'minimize': False,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
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
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'AssertTest.test_assert_true()'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )
    assert_pass(test, single(prove_res))

    foundry_remove_node(foundry, options=RemoveNodeOptions({'test': test, 'node': 8}))

    proof = foundry.get_optional_proof(single(foundry.proof_ids_with_test(test)))
    assert type(proof) is APRProof
    assert proof.pending

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )
    assert_pass(test, single(prove_res))


def test_foundry_resume_proof(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'AssumeTest.test_assume_false(uint256,uint256)'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'auto_abstract_gas': True,
                'max_iterations': 4,
                'bug_report': bug_report,
                'break_on_calls': True,
                'reinit': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    proof = single(prove_res)
    assert isinstance(proof, APRProof)
    assert proof.pending

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'auto_abstract_gas': True,
                'max_iterations': 10,
                'reinit': False,
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
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
    force_sequential: bool,
) -> None:
    if no_use_booster or test_id in SKIPPED_INIT_CODE_TESTS:
        pytest.skip()

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'run_constructor': True,
                'bug_report': bug_report,
                'fail_fast': False,
                'use_booster': not no_use_booster,
                'force_sequential': force_sequential,
            }
        ),
    )

    assert_pass(test_id, single(prove_res))


def test_foundry_duplicate_contract_names(foundry: Foundry) -> None:
    assert 'src%duplicates%1%DuplicateName' in foundry.contracts.keys()
    assert 'src%duplicates%2%DuplicateName' in foundry.contracts.keys()


def test_load_state_diff(
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
    output_dir = foundry._root / foundry.profile.get('test', '')
    foundry_state_load(
        LoadStateOptions(
            {
                'name': 'LoadStateDiff',
                'accesses_file': TEST_DATA_DIR / 'accesses.json',
                'output_dir_name': 'src',
                'from_state_diff': 'True',
            }
        ),
        output_dir=output_dir,
    )

    generated_main_file = foundry_root_dir / 'src' / 'LoadStateDiff.sol'
    generated_code_file = foundry_root_dir / 'src' / 'LoadStateDiffCode.sol'

    assert_or_update_show_output(
        generated_main_file.read_text(),
        TEST_DATA_DIR / 'foundry' / 'src' / 'LoadStateDiff.sol',
        update=update_expected_output,
    )
    assert_or_update_show_output(
        generated_code_file.read_text(),
        TEST_DATA_DIR / 'foundry' / 'src' / 'LoadStateDiffCode.sol',
        update=update_expected_output,
    )


def test_load_state_dump(
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
    output_dir = foundry._root / foundry.profile.get('test', '')
    foundry_state_load(
        LoadStateOptions(
            {
                'name': 'LoadStateDump',
                'accesses_file': TEST_DATA_DIR / 'dumpState.json',
                'output_dir_name': 'src',
            }
        ),
        output_dir=output_dir,
    )

    generated_main_file = foundry_root_dir / 'src' / 'LoadStateDump.sol'
    generated_code_file = foundry_root_dir / 'src' / 'LoadStateDumpCode.sol'

    assert_or_update_show_output(
        generated_main_file.read_text(),
        TEST_DATA_DIR / 'foundry' / 'src' / 'LoadStateDump.sol',
        update=update_expected_output,
    )
    assert_or_update_show_output(
        generated_code_file.read_text(),
        TEST_DATA_DIR / 'foundry' / 'src' / 'LoadStateDumpCode.sol',
        update=update_expected_output,
    )


def test_foundry_refute_node(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'AssertTest.test_assert_true_branch(uint256)'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res_1 = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    # Test initially passes, no pending nodes
    assert_pass(test, single(prove_res_1))
    check_pending(foundry, test, [])

    # Remove successors of nodes 9 and 10
    foundry_remove_node(foundry, RemoveNodeOptions({'test': test, 'node': 11}))
    foundry_remove_node(foundry, RemoveNodeOptions({'test': test, 'node': 12}))

    # Now nodes 9 and 10 are pending
    check_pending(foundry, test, [9, 10])

    # Mark node 9 as refuted
    foundry_refute_node(foundry, RefuteNodeOptions({'test': test, 'node': 9}))

    # Refuted node is not longer pending
    check_pending(foundry, test, [10])

    # Proof will only advance from node 10, since 9 is refuted
    prove_res_2 = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    # Test no longer passing since there are refuted nodes
    assert not single(prove_res_2).passed

    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
    )

    assert_or_update_show_output(
        show_res, TEST_DATA_DIR / 'show/node-refutation.expected', update=update_expected_output
    )

    check_pending(foundry, test, [])

    # Remove refutation of node 9
    foundry_unrefute_node(foundry, UnrefuteNodeOptions({'test': test, 'node': 9}))

    check_pending(foundry, test, [9])

    # Execution will continue from node 9
    prove_res_3 = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    # Proof passes again
    assert_pass(test, single(prove_res_3))


def test_foundry_extra_lemmas(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'ArithmeticTest.test_xor(uint256,uint256)'
    lemmas_file = 'xor-lemmas.k'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
                'lemmas': f'{TEST_DATA_DIR / lemmas_file}:XOR-LEMMAS',
            }
        ),
    )

    assert_pass(test, single(prove_res))


def test_foundry_xml_report(
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [
                    ('AssertTest.test_assert_true()', None),
                    ('AssertTest.test_assert_false()', None),
                    ('AssertNestedTest.test_assert_true_nested()', None),
                ],
                'bug_report': bug_report,
                'port': server.port,
                'xml_test_report': True,
                'force_sequential': force_sequential,
            }
        ),
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
    force_sequential: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'PrankTest.testSymbolicStartPrank'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res_1 = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    assert_pass(test, single(prove_res_1))

    # Remove node with non-deterministic branch
    foundry_remove_node(foundry, RemoveNodeOptions({'test': test, 'node': 13}))

    split_nodes = foundry_split_node(
        foundry,
        SplitNodeOptions(
            {
                'test': test,
                'node': 12,
                'branch_condition': 'VV0_addr_114b9705 ==Int 491460923342184218035706888008750043977755113263',
            }
        ),
    )
    assert split_nodes == [70, 71]

    split_nodes = foundry_split_node(
        foundry,
        SplitNodeOptions(
            {
                'test': test,
                'node': 71,
                'branch_condition': 'VV0_addr_114b9705 ==Int 645326474426547203313410069153905908525362434349',
            }
        ),
    )
    assert split_nodes == [72, 73]

    split_nodes = foundry_split_node(
        foundry,
        options=SplitNodeOptions(
            {
                'test': test,
                'node': 73,
                'branch_condition': 'VV0_addr_114b9705 ==Int 728815563385977040452943777879061427756277306518',
            }
        ),
    )
    assert split_nodes == [74, 75]

    foundry_refute_node(foundry, RefuteNodeOptions({'test': test, 'node': 70}))
    foundry_refute_node(foundry, RefuteNodeOptions({'test': test, 'node': 72}))
    foundry_refute_node(foundry, RefuteNodeOptions({'test': test, 'node': 74}))

    check_pending(foundry, test, [75])

    prove_res_2 = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'port': server.port,
                'force_sequential': force_sequential,
            }
        ),
    )

    assert not single(prove_res_2).passed

    show_res = foundry_show(
        foundry=foundry,
        options=ShowOptions(
            {
                'test': test,
                'to_module': True,
                'sort_collections': True,
                'omit_unstable_output': True,
                'pending': True,
                'failing': True,
                'failure_info': True,
                'port': server.port,
            }
        ),
    )

    assert_or_update_show_output(show_res, TEST_DATA_DIR / 'show/split-node.expected', update=update_expected_output)


def test_foundry_prove_skips_setup(
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
    force_sequential: bool,
) -> None:
    def assert_correct_ids_generted(
        proofs: list[APRProof],
        test_name: str,
        expected_test_ver: int,
        expected_setup_ver: int,
        expect_setup_exists: bool,
    ) -> None:
        for p in proofs:
            if test_name in p.id:
                assert int(p.id.split(':')[1]) == expected_test_ver
                setup_ver = p.id.split('.')[0] + '.setUp():' + str(expected_setup_ver)
                setup_dir = Path('') if p.proof_dir is None else p.proof_dir
                assert Proof.proof_data_exists(setup_ver, setup_dir) == expect_setup_exists

    def run_prover(test_name: str, _reinit: bool, _setup_version: int | None = None) -> list[APRProof]:
        return foundry_prove(
            foundry=foundry,
            options=ProveOptions(
                {
                    'tests': [(test_name, None)],
                    'bug_report': bug_report,
                    'reinit': _reinit,
                    'setup_version': _setup_version,
                    'port': server.port,
                    'force_sequential': force_sequential,
                }
            ),
        )

    if no_use_booster:
        pytest.skip()

    test_a = 'ContractBTest.testNumberIs42'
    test_b = 'ContractBTest.testFailSubtract43'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    prove_res = run_prover(test_a, _reinit=True, _setup_version=None)
    assert_correct_ids_generted(prove_res, test_a, expected_test_ver=0, expected_setup_ver=0, expect_setup_exists=True)

    prove_res = run_prover(test_a, _reinit=True, _setup_version=0)
    assert_correct_ids_generted(prove_res, test_a, expected_test_ver=1, expected_setup_ver=0, expect_setup_exists=True)
    assert_correct_ids_generted(prove_res, test_a, expected_test_ver=1, expected_setup_ver=1, expect_setup_exists=False)

    prove_res = run_prover(test_a, _reinit=True, _setup_version=None)
    assert_correct_ids_generted(prove_res, test_a, expected_test_ver=2, expected_setup_ver=0, expect_setup_exists=True)
    assert_correct_ids_generted(prove_res, test_a, expected_test_ver=2, expected_setup_ver=1, expect_setup_exists=True)

    prove_res = run_prover(test_b, _reinit=True, _setup_version=1)
    assert_correct_ids_generted(prove_res, test_b, expected_test_ver=0, expected_setup_ver=0, expect_setup_exists=True)
    assert_correct_ids_generted(prove_res, test_b, expected_test_ver=0, expected_setup_ver=1, expect_setup_exists=True)

    prove_res = run_prover(test_b, _reinit=True, _setup_version=None)
    assert_correct_ids_generted(prove_res, test_b, expected_test_ver=1, expected_setup_ver=0, expect_setup_exists=True)
    assert_correct_ids_generted(prove_res, test_b, expected_test_ver=1, expected_setup_ver=1, expect_setup_exists=True)
    assert_correct_ids_generted(prove_res, test_b, expected_test_ver=1, expected_setup_ver=2, expect_setup_exists=True)
