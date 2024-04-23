from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pyk.proof import APRProof
from pyk.proof.reachability import APRFailureInfo
from pyk.utils import single

from kontrol.prove import ProveOptions, foundry_prove

if TYPE_CHECKING:
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.proof.proof import Proof
    from pyk.utils import BugReport

    from kontrol.foundry import Foundry


sys.setrecursionlimit(10**7)

TEST_DATA_DIR: Final = (Path(__file__).parent / 'test-data').resolve(strict=True)

ALL_PROVE_TESTS: Final = tuple((TEST_DATA_DIR / 'kontrol-prove-all').read_text().splitlines())


@pytest.mark.parametrize('test_id', ALL_PROVE_TESTS)
def test_kontrol_prove(
    test_id: str,
    foundry: Foundry,
    update_expected_output: bool,
    no_use_booster: bool,
    bug_report: BugReport | None,
    server: KoreServer,
) -> None:

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    # When
    prove_res = foundry_prove(
        foundry=foundry,
        options=ProveOptions(
            {
                'tests': [(test_id, None)],
                'bug_report': bug_report,
                'break_on_calls': True,
                'use_gas': False,
                'port': server.port,
            }
        ),
    )

    # Then
    assert_pass(test_id, single(prove_res))


def assert_pass(test: str, proof: Proof) -> None:
    if not proof.passed:
        if isinstance(proof, APRProof):
            assert proof.failure_info
            assert isinstance(proof.failure_info, APRFailureInfo)
            pytest.fail('\n'.join(proof.failure_info.print()))
        else:
            pytest.fail()
