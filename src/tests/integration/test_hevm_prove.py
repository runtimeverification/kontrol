from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest
from pyk.proof import APRProof
from pyk.proof.reachability import APRFailureInfo
from pyk.utils import single

from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

if TYPE_CHECKING:
    from typing import Final

    from pyk.kore.rpc import KoreServer
    from pyk.proof.proof import Proof
    from pyk.utils import BugReport

    from kontrol.foundry import Foundry


sys.setrecursionlimit(10**7)


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
