from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from kevm_pyk.kevm import KEVM
from pyk.kast.inner import KApply, KToken, KVariable

from kontrol.solc_to_k import Contract, Input, _range_predicate

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from typing import Final

    from pyk.kast.inner import KInner


EXAMPLES_DIR: Final = TEST_DATA_DIR / 'examples'

PREDICATE_DATA: list[tuple[str, KInner, str, KInner | None]] = [
    ('bytes4', KVariable('V0_x'), 'bytes4', KEVM.range_bytes(KToken('4', 'Int'), KVariable('V0_x'))),
    ('int128', KVariable('V0_x'), 'int128', KEVM.range_sint(128, KVariable('V0_x'))),
    ('int24', KVariable('V0_x'), 'int24', KEVM.range_sint(24, KVariable('V0_x'))),
    ('uint24', KVariable('V0_x'), 'uint24', KEVM.range_uint(24, KVariable('V0_x'))),
]


@pytest.mark.parametrize(
    'test_id,term,type,expected',
    PREDICATE_DATA,
    ids=[test_id for test_id, *_ in PREDICATE_DATA],
)
def test_range_predicate(test_id: str, term: KInner, type: str, expected: KInner | None) -> None:
    # When
    ret = _range_predicate(term, type)

    # Then
    assert ret == expected


ESCAPE_DATA: list[tuple[str, str, str, str]] = [
    ('has_underscore', 'S2K', 'My_contract', 'S2KMyZUndcontract'),
    ('no_change', '', 'mycontract', 'mycontract'),
    ('starts_underscore', 'S2K', '_method', 'S2KZUndmethod'),
    ('with_escape', '', 'Z_', 'ZZZUnd'),
    ('lower_z', '', 'z_', 'zZUnd'),
    ('with_escape_no_prefix', 'S2K', 'zS2K_', 'S2KzS2KZUnd'),
    ('doll', 'S2K', '$name', 'S2KZDlrname'),
]


@pytest.mark.parametrize('test_id,prefix,input,output', ESCAPE_DATA, ids=[test_id for test_id, *_ in ESCAPE_DATA])
def test_escaping(test_id: str, prefix: str, input: str, output: str) -> None:
    # When
    escaped = Contract.escaped(input, prefix)

    # Then
    assert escaped == output

    # And When
    unescaped = Contract.unescaped(output, prefix)

    # Then
    assert unescaped == input


ABI_INPUT_DATA: list[tuple[str, str, Input]] = [
    (
        'multidimensional-array',
        """{
                "internalType": "uint256[3][2]",
                "name": "p1",
                "type": "uint256[3][2]"
        }""",
        Input('', 'p1', 'uint256[3][2]', []),
    ),
    (
        'nested-structs',
        """{
                "components": [
                  {
                    "internalType": "uint256",
                    "name": "a",
                    "type": "uint256"
                  },
                  {
                    "internalType": "address",
                    "name": "b",
                    "type": "address"
                  },
                  {
                    "components": [
                      {
                        "internalType": "uint256",
                        "name": "e",
                        "type": "uint256"
                      }
                    ],
                    "internalType": "struct Nested[2]",
                    "name": "c",
                    "type": "tuple[2]"
                  }
                ],
                "internalType": "struct Vars[2][3]",
                "name": "sArray",
                "type": "tuple[2][3]"
        }""",
        Input(
            '',
            'sArray',
            'tuple[2][3]',
            [
                Input('sArray[][]', 'a', 'uint256'),
                Input('sArray[][]', 'b', 'address'),
                Input('sArray[][]', 'c', 'tuple[2]', [Input('sArray[][].c[]', 'e', 'uint256')]),
            ],
        ),
    ),
]


@pytest.mark.parametrize('test_id,abi_input,expected', ABI_INPUT_DATA, ids=[test_id for test_id, *_ in ABI_INPUT_DATA])
def test_input_from_dict(test_id: str, abi_input: str, expected: Input) -> None:
    input_json = json.loads(abi_input)
    input = Input.from_dict(input_json)
    assert input == expected


INPUT_DATA: list[tuple[str, Input, KApply]] = [
    ('single_type', Input('', 'RV', 'uint256'), KApply('abi_type_uint256', [KVariable('RV')])),
    ('empty_tuple', Input('', 'EmptyStruct', 'tuple'), KEVM.abi_tuple([])),
    (
        'single_tuple',
        Input('', 'SomeStruct', 'tuple', [Input('', 'RV1', 'uint256'), Input('', 'RV2', 'uint256')]),
        KEVM.abi_tuple(
            [KApply('abi_type_uint256', [KVariable('RV1')]), KApply('abi_type_uint256', [KVariable('RV2')])]
        ),
    ),
    (
        'nested_tuple',
        Input(
            '',
            'SomeStruct',
            'tuple',
            [
                Input('SomeStruct', 'RV', 'uint256'),
                Input('SomeStruct', 'SomeStruct', 'tuple', [Input('SomeStruct.SomeStruct', 'RV', 'uint256')]),
            ],
        ),
        KEVM.abi_tuple(
            [
                KApply('abi_type_uint256', [KVariable('SomeStruct.RV')]),
                KEVM.abi_tuple([KApply('abi_type_uint256', [KVariable('SomeStruct.SomeStruct.RV')])]),
            ]
        ),
    ),
]


@pytest.mark.parametrize('test_id,input,expected', INPUT_DATA, ids=[test_id for test_id, *_ in INPUT_DATA])
def test_input_to_abi(test_id: str, input: Input, expected: KApply) -> None:
    # When
    abi = input.to_abi()

    # Then
    assert abi == expected
