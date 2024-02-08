from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from kevm_pyk.kevm import KEVM
from pyk.kast.inner import KApply, KToken, KVariable

from kontrol.solc_to_k import Contract, Input, _range_predicates, find_function_calls, process_length_equals

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

DEVDOCS_DATA: list[tuple[str, dict, dict, tuple[int, ...] | None, int | None]] = [
    (
        'test_1',
        {'_withdrawalProof': 10, '_withdrawalProof[]': 600, 'data': 600},
        {'name': '_withdrawalProof', 'type': 'bytes[]'},
        (10,),
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
def test_process_length_equals(
    test_id: str,
    devdocs: dict,
    input_dict: dict,
    expected_array_length: list[int] | None,
    expected_dynamic_type_length: int | None,
) -> None:
    # When
    array_lengths, dyn_len = process_length_equals(input_dict, devdocs)
    assert array_lengths == expected_array_length
    assert dyn_len == expected_dynamic_type_length


AST_DATA: list[tuple[str, dict, list[str]]] = [
    (
        'skip_first',
        {
            'nodeType': 'FunctionDefinition',
            'body': {
                'statements': [
                    {
                        'expression': {
                            'arguments': [],
                            'expression': {
                                'expression': {
                                    'typeDescriptions': {
                                        'typeString': 'contract KEVMCheatsBase',
                                    },
                                },
                                'memberName': 'infiniteGas',
                                'nodeType': 'MemberAccess',
                                'typeDescriptions': {
                                    'typeString': 'function () external',
                                },
                            },
                            'nodeType': 'FunctionCall',
                        },
                    },
                    {
                        'expression': {
                            'arguments': [
                                {'typeDescriptions': {'typeString': 'uint256'}},
                                {'typeDescriptions': {'typeString': 'bool'}},
                            ],
                            'expression': {
                                'expression': {
                                    'typeDescriptions': {
                                        'typeString': 'contract Counter',
                                    },
                                },
                                'memberName': 'setNumber',
                                'nodeType': 'MemberAccess',
                                'typeDescriptions': {
                                    'typeString': 'function (uint256,bool) external',
                                },
                            },
                            'nodeType': 'FunctionCall',
                        },
                    },
                    {
                        'expression': {
                            'arguments': [],
                            'expression': {
                                'expression': {
                                    'typeDescriptions': {
                                        'typeString': 'contract Counter',
                                    },
                                },
                                'memberName': 'number',
                                'nodeType': 'MemberAccess',
                                'typeDescriptions': {
                                    'typeString': 'function () view external returns (uint256)',
                                },
                            },
                            'nodeType': 'FunctionCall',
                        },
                    },
                ],
            },
        },
        ['Counter.setNumber(uint256,bool)', 'Counter.number()'],
    ),
    (
        'duplicated_with_const',
        {
            'nodeType': 'FunctionDefinition',
            'body': {
                'statements': [
                    {
                        'expression': {
                            'arguments': [
                                {'typeDescriptions': {'typeString': 'uint256'}},
                                {'typeDescriptions': {'typeString': 'uint256'}},
                            ],
                            'expression': {
                                'expression': {
                                    'typeDescriptions': {
                                        'typeString': 'contract ArithmeticContract',
                                    },
                                },
                                'memberName': 'add',
                                'nodeType': 'MemberAccess',
                                'typeDescriptions': {
                                    'typeString': 'function (uint256,uint256) pure external returns (uint256)',
                                },
                            },
                            'nodeType': 'FunctionCall',
                        },
                    },
                    {
                        'expression': {
                            'arguments': [
                                {'typeIdentifier': 't_uint256', 'typeString': 'uint256'},
                                {'typeIdentifier': 't_rational_1_by_1', 'typeString': 'int_const 1'},
                            ],
                            'expression': {
                                'expression': {
                                    'typeDescriptions': {
                                        'typeString': 'contract ArithmeticContract',
                                    },
                                },
                                'memberName': 'add',
                                'nodeType': 'MemberAccess',
                                'typeDescriptions': {
                                    'typeString': 'function (uint256,uint256) pure external returns (uint256)',
                                },
                            },
                            'nodeType': 'FunctionCall',
                        },
                    },
                ],
            },
        },
        ['ArithmeticContract.add(uint256,uint256)'],
    ),
]


@pytest.mark.parametrize(
    'test_id,ast,expected',
    AST_DATA,
    ids=[test_id for test_id, *_ in AST_DATA],
)
def test_find_function_calls(test_id: str, ast: dict, expected: list[str]) -> None:
    # When
    output = find_function_calls(ast)
    # Then
    assert output == expected
