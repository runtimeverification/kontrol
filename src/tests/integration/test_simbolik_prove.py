from __future__ import annotations

from typing import TYPE_CHECKING

from pyk.kast.inner import KSort, KToken
from pyk.utils import single

from kontrol.foundry import Foundry
from kontrol.options import ProveOptions, RPCOptions
from kontrol.prove import foundry_prove

from .test_foundry_prove import assert_pass, foundry, server  # noqa: F403

if TYPE_CHECKING:

    from pyk.kore.rpc import KoreServer
    from pyk.utils import BugReport


def test_simbolik_prove(
    foundry: Foundry,
    bug_report: BugReport | None,
    server: KoreServer,
) -> None:
    test_id = "SimbolikCode.getNumber()"

    prove_options = ProveOptions(
        bug_report=bug_report,
        active_symbolik=True,
    )

    # When
    prove_res = foundry_prove(
        foundry,
        tests=[(test_id, None)],
        prove_options=prove_options,
        rpc_options=RPCOptions(port=server.port, smt_timeout=500),
    )

    # Then
    proof = single(prove_res)
    assert_pass(test_id, proof)

    # All accounts must have a concrete address and code cell
    init_node = proof.kcfg.node(proof.init)

    accounts = init_node.cterm.cells.get("ACCOUNTS_CELL", None)
    assert accounts is not None
    assert 0 < len(accounts.args)

    empty = foundry.kevm.definition.empty_config(KSort("AccountCell"))
    for account in accounts.args:
        subst = empty.match(account)
        assert subst is not None
        acct_id = subst.get("ACCTID_CELL", None)
        assert isinstance(acct_id, KToken)
        code = subst.get("CODE_CELL", None)
        assert isinstance(code, KToken)
