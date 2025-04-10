from __future__ import annotations

import sys
import xml.etree.ElementTree as Et
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pyk.proof import APRProof
from pyk.proof.proof import Proof
from pyk.utils import single

from kontrol.foundry import (
    Foundry,
    foundry_merge_nodes,
    foundry_minimize_proof,
    foundry_refute_node,
    foundry_remove_node,
    foundry_show,
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
