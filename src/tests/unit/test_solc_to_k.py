from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from kevm_pyk.kevm import KEVM
from pyk.kast.inner import KApply, KToken, KVariable

from kontrol.solc_to_k import Contract, Input, _range_predicates, get_input_length

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from typing import Final


EXAMPLES_DIR: Final = TEST_DATA_DIR / 'examples'

PREDICATE_DATA: list[tuple[str, KApply, list[KApply]]] = [
    ('bytes4', KApply('bytes4', KVariable('V0_x')), [KEVM.range_bytes(KToken('4', 'Int'), KVariable('V0_x'))]),
    ('int128', KApply('int128', KVariable('V0_x')), [KEVM.range_sint(128, KVariable('V0_x'))]),
    ('int24', KApply('int24', KVariable('V0_x')), [KEVM.range_sint(24, KVariable('V0_x'))]),
    ('uint24', KApply('uint24', KVariable('V0_x')), [KEVM.range_uint(24, KVariable('V0_x'))]),
    (
        'tuple',
        KApply(
            'abi_type_tuple',
            [
                KApply(
                    '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                    [
                        KApply('abi_type_uint256', [KVariable('V0_x')]),
                        KApply(
                            '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                            [
                                KApply('abi_type_uint256', [KVariable('V1_y')]),
                                KApply(
                                    '.List{"_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs"}_TypedArgs',
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),
        [KEVM.range_uint(256, KVariable('V0_x')), KEVM.range_uint(256, KVariable('V1_y'))],
    ),
    (
        'nested_tuple',
        KApply(
            'abi_type_tuple',
            KApply(
                '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                KApply('abi_type_uint256', [KVariable('V0_x')]),
                KApply(
                    '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                    KApply(
                        'abi_type_tuple',
                        KApply(
                            '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                            KApply('abi_type_uint256', [KVariable('V1_y')]),
                            KApply(
                                '.List{"_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs"}_TypedArgs',
                            ),
                        ),
                    ),
                    KApply(
                        '.List{"_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs"}_TypedArgs',
                    ),
                ),
            ),
        ),
        [KEVM.range_uint(256, KVariable('V0_x')), KEVM.range_uint(256, KVariable('V1_y'))],
    ),
]


@pytest.mark.parametrize(
    'test_id,term,expected',
    PREDICATE_DATA,
    ids=[test_id for test_id, *_ in PREDICATE_DATA],
)
def test_range_predicate(test_id: str, term: KApply, expected: list[KApply]) -> None:
    # When
    ret = _range_predicates(term)

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


INPUT_DATA: list[tuple[str, Input, KApply]] = [
    ('single_type', Input('RV', 'uint256'), KApply('abi_type_uint256', [KVariable('V0_RV')])),
    (
        'empty_tuple',
        Input('EmptyStruct', 'tuple'),
        KApply('abi_type_tuple', KApply('.List{"_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs"}_TypedArgs')),
    ),
    (
        'single_tuple',
        Input('SomeStruct', 'tuple', (Input('RV1', 'uint256'), Input('RV2', 'uint256', idx=1))),
        KApply(
            'abi_type_tuple',
            KApply(
                '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                KApply('abi_type_uint256', [KVariable('V0_RV1')]),
                KApply(
                    '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                    KApply('abi_type_uint256', [KVariable('V1_RV2')]),
                    KApply(
                        '.List{"_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs"}_TypedArgs',
                    ),
                ),
            ),
        ),
    ),
    (
        'nested_tuple',
        Input(
            'SomeStruct',
            'tuple',
            (Input('RV', 'uint256'), Input('SomeStruct', 'tuple', (Input('RV', 'uint256', idx=1),))),
        ),
        KApply(
            'abi_type_tuple',
            KApply(
                '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                KApply('abi_type_uint256', [KVariable('V0_RV')]),
                KApply(
                    '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                    KApply(
                        'abi_type_tuple',
                        KApply(
                            '_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs',
                            KApply('abi_type_uint256', [KVariable('V1_RV')]),
                            KApply(
                                '.List{"_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs"}_TypedArgs',
                            ),
                        ),
                    ),
                    KApply(
                        '.List{"_,__EVM-ABI_TypedArgs_TypedArg_TypedArgs"}_TypedArgs',
                    ),
                ),
            ),
        ),
    ),
]

DEVDOCS_DATA: list[tuple[str, dict, dict, list[int] | None, int | None]] = [
    (
        'test_1',
        {'_withdrawalProof': 10, '_withdrawalProof[]': 600, 'data': 600},
        {'name': '_withdrawalProof', 'type': 'bytes[]'},
        [10],
        600,
    ),
    ('test_2', {}, {'name': '_a', 'type': 'bytes'}, None, None),
]


@pytest.mark.parametrize('test_id,input,expected', INPUT_DATA, ids=[test_id for test_id, *_ in INPUT_DATA])
def test_input_to_abi(test_id: str, input: Input, expected: KApply) -> None:
    # When
    abi = input.to_abi()

    # Then
    assert abi == expected


@pytest.mark.parametrize(
    'test_id,devdocs,input_dict,expected_array_length, expected_dynamic_type_length',
    DEVDOCS_DATA,
    ids=[test_id for test_id, *_ in DEVDOCS_DATA],
)
def test_get_input_length(
    test_id: str,
    devdocs: dict,
    input_dict: dict,
    expected_array_length: list[int] | None,
    expected_dynamic_type_length: int | None,
) -> None:
    # When
    array_lengths, dyn_len = get_input_length(input_dict, devdocs)

    # Then
    assert array_lengths == expected_array_length
    assert dyn_len == expected_dynamic_type_length


ABI_DATA: list[tuple[str, dict, dict, Input]] = [
    (
        'test_tuple',
        {
            'components': [
                {'internalType': 'uint256', 'name': 'nonce', 'type': 'uint256'},
                {'internalType': 'address', 'name': 'sender', 'type': 'address'},
                {'internalType': 'address', 'name': 'target', 'type': 'address'},
                {'internalType': 'uint256', 'name': 'value', 'type': 'uint256'},
                {'internalType': 'uint256', 'name': 'gasLimit', 'type': 'uint256'},
                {'internalType': 'bytes', 'name': 'data', 'type': 'bytes'},
            ],
            'internalType': 'struct CallDataTest.WithdrawalTransaction',
            'name': '_tx',
            'type': 'tuple',
        },
        {'_withdrawalProof': 10, '_withdrawalProof[]': 600, 'data': 600},
        Input(
            name='_tx',
            type='tuple',
            components=(
                Input(name='nonce', type='uint256', components=(), idx=0, array_lengths=None, dynamic_type_length=None),
                Input(
                    name='sender',
                    type='address',
                    components=(),
                    idx=1,
                    array_lengths=None,
                    dynamic_type_length=None,
                ),
                Input(
                    name='target',
                    type='address',
                    components=(),
                    idx=2,
                    array_lengths=None,
                    dynamic_type_length=None,
                ),
                Input(name='value', type='uint256', components=(), idx=3, array_lengths=None, dynamic_type_length=None),
                Input(
                    name='gasLimit',
                    type='uint256',
                    components=(),
                    idx=4,
                    array_lengths=None,
                    dynamic_type_length=None,
                ),
                Input(name='data', type='bytes', components=(), idx=5, array_lengths=None, dynamic_type_length=600),
            ),
            idx=0,
            array_lengths=None,
            dynamic_type_length=None,
        ),
    )
]


@pytest.mark.parametrize('test_id,input_dict,devdocs,expected', ABI_DATA, ids=[test_id for test_id, *_ in ABI_DATA])
def test_input_from_dict(test_id: str, input_dict: dict, devdocs: dict, expected: Input) -> None:
    # When
    _input = Input.from_dict(input_dict, natspec_lengths=devdocs)

    # Then
    assert _input == expected
