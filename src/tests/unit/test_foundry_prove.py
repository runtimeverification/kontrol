from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KLabel, KSequence, KSort, KToken, KVariable

from kontrol.state_record import read_recorded_state_diff, recorded_state_to_account_cells
from kontrol.utils import decode_log_message, ensure_name_is_unique

from .utils import (
    TEST_DATA_DIR,
)

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
                        label=KLabel(name='parseByteStack'),
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
            KApply(label=KLabel(name='<transientStorage>'), args=(KApply(label=KLabel(name='.Map'), args=()),)),
            KApply(label=KLabel(name='<nonce>'), args=(KToken(token='0', sort=KSort(name='Int')),)),
        ),
    )
]


def test_recorded_state_to_account_cells() -> None:
    # Given
    deployment_state_entries = read_recorded_state_diff(state_file=ACCESSES_INPUT_FILE)

    # When
    actual = recorded_state_to_account_cells(deployment_state_entries)

    # Then
    assert actual == ACCOUNTS_EXPECTED


TEST_DATA = [
    ('single-var', 'NEWVAR', CTerm(KApply('<k>', KVariable('NEWVAR')), []), 'NEWVAR_0'),
    (
        'sequence-check',
        'NEWVAR',
        CTerm(KApply('<k>', KSequence(KApply('_+Int_', [KVariable('NEWVAR'), KVariable('NEWVAR_0')]))), []),
        'NEWVAR_1',
    ),
]


@pytest.mark.parametrize('test_id,name,config,expected', TEST_DATA, ids=[test_id for test_id, *_ in TEST_DATA])
def test_ensure_name_is_unique(test_id: str, name: str, config: CTerm, expected: str) -> None:
    # Given

    # When
    actual = ensure_name_is_unique(name, config)

    # Then
    assert actual == expected


DECODE_TEST_DATA: Final = [
    ('empty', 1368866505, 'b""', ''),
    (
        'empty-string',
        196436950,
        'b"\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00 \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"',
        '',
    ),
    (
        'string-int',
        3054400204,
        'b"\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00@\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x16Test contract balance:\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"',
        'Test contract balance: 79228162514264337593543950335',
    ),
]


@pytest.mark.parametrize(
    'test_id,log_selector,input,expected', DECODE_TEST_DATA, ids=[test_id for test_id, *_ in DECODE_TEST_DATA]
)
def test_abi_decode(test_id: str, log_selector: int, input: str, expected: str) -> None:
    # Given

    # When
    actual = decode_log_message(input, log_selector)

    # Then
    assert actual == expected
