from __future__ import annotations

from typing import TYPE_CHECKING

from pyk.kast.inner import KApply, KLabel, KSort, KToken

from kontrol.foundry import read_deployment_state
from kontrol.prove import summary_to_account_cells

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from typing import Final

ACCESSES_INPUT_FILE: Final = TEST_DATA_DIR / 'accesses.json'
ACCOUNTS_EXPECTED: Final = [
    KApply(
        label=KLabel(name='<account>'),
        args=(
            KApply(
                label=KLabel(name='<acctID>'),
                args=(KToken(token='491460923342184218035706888008750043977755113263', sort=KSort(name='Int')),),
            ),
            KApply(label=KLabel(name='<balance>'), args=(KToken(token='0', sort=KSort(name='Int')),)),
            KApply(
                label=KLabel(name='<code>'),
                args=(
                    KApply(
                        label=KLabel(name='#parseByteStack(_)_SERIALIZATION_Bytes_String'),
                        args=(
                            KToken(
                                token='"0x6080604052348015600f57600080fd5b5060043610603c5760003560e01c80633fb5c1cb1460415780638381f58a146053578063d09de08a14606d575b600080fd5b6051604c3660046083565b600055565b005b605b60005481565b60405190815260200160405180910390f35b6051600080549080607c83609b565b9190505550565b600060208284031215609457600080fd5b5035919050565b60007fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff820360f2577f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b506001019056fea164736f6c634300080f000a"',
                                sort=KSort(name='String'),
                            ),
                        ),
                    ),
                ),
            ),
            KApply(
                label=KLabel(name='<storage>'),
                args=(
                    KApply(
                        label=KLabel(name='_|->_'),
                        args=(KToken(token='0', sort=KSort(name='Int')), KToken(token='3', sort=KSort(name='Int'))),
                    ),
                ),
            ),
            KApply(label=KLabel(name='<origStorage>'), args=(KApply(label=KLabel(name='.Map'), args=()),)),
            KApply(label=KLabel(name='<nonce>'), args=(KToken(token='0', sort=KSort(name='Int')),)),
        ),
    )
]


def test_summary_to_account_cells() -> None:
    # Given
    deployment_state_entries = read_deployment_state(accesses_file=ACCESSES_INPUT_FILE)

    # When
    actual = summary_to_account_cells(deployment_state_entries)

    # Then
    assert actual == ACCOUNTS_EXPECTED
