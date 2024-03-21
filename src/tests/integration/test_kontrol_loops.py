from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from kontrol.foundry import (
    foundry_merge_nodes,
    foundry_refute_node,
    foundry_remove_node,
    foundry_show,
    foundry_step_node,
    foundry_unrefute_node,
)
from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

from .utils import TEST_DATA_DIR, assert_or_update_show_output

if TYPE_CHECKING:
    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport

    from kontrol.foundry import Foundry

sys.setrecursionlimit(10**7)


def test_foundry_loop_invariant(
    foundry: Foundry,
    update_expected_output: bool,
    bug_report: BugReport | None,
    server: KoreServer,
    no_use_booster: bool,
) -> None:
    if no_use_booster:
        pytest.skip()

    test = 'PortalTest.test_withdrawal_paused((uint256,address,address,uint256,uint256,bytes),uint256,(bytes32,bytes32,bytes32,bytes32),bytes[])'

    if bug_report is not None:
        server._populate_bug_report(bug_report)

    foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(max_iterations=10, bug_report=bug_report, break_on_calls=False),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    foundry_remove_node(foundry, test, node=18)

    foundry_step_node(
        foundry,
        test,
        node=15,
        depth=4,
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    foundry_refute_node(foundry, test, node=19)

    foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(max_iterations=8, bug_report=bug_report, break_on_calls=False),
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    foundry_remove_node(foundry, test, node=24)

    foundry_step_node(
        foundry,
        test,
        node=22,
        depth=4,
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    foundry_step_node(
        foundry,
        test,
        node=28,
        depth=4,
        rpc_options=RPCOptions(
            port=server.port,
        ),
    )

    foundry_refute_node(foundry, test, node=29)
    foundry_unrefute_node(foundry, test, node=19)
    foundry_merge_nodes(foundry, test, node_ids=[19, 30, 31], include_disjunct=True)

    foundry_prove(
        foundry,
        tests=[(test, None)],
        prove_options=ProveOptions(bug_report=bug_report, break_on_calls=True),
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
        show_res, TEST_DATA_DIR / 'show/IX-loop-invariant.expected', update=update_expected_output
    )
