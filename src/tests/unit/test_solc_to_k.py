from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from kevm_pyk.kevm import KEVM
from pyk.kast.inner import KApply, KToken, KVariable
from pyk.kast.prelude.kint import eqInt, intToken

from kontrol.solc_to_k import (
    Contract,
    Input,
    StorageField,
    _contract_name_from_bytecode,
    _range_predicates,
    decode_kinner_output,
    find_function_calls,
    process_length_equals,
    process_storage_layout,
)

if TYPE_CHECKING:
    from pyk.kast.inner import KInner

PREDICATE_DATA: list[tuple[str, KApply, int | None, list[KApply]]] = [
    ('bytes4', KApply('bytes4', KVariable('V0_x')), None, [KEVM.range_bytes(intToken(4), KVariable('V0_x'))]),
    ('bytes', KApply('bytes', KVariable('V0_x')), 10000, [eqInt(KEVM.size_bytes(KVariable('V0_x')), intToken(10000))]),
    ('int128', KApply('int128', KVariable('V0_x')), None, [KEVM.range_sint(128, KVariable('V0_x'))]),
    ('int24', KApply('int24', KVariable('V0_x')), None, [KEVM.range_sint(24, KVariable('V0_x'))]),
    ('uint24', KApply('uint24', KVariable('V0_x')), None, [KEVM.range_uint(24, KVariable('V0_x'))]),
    (
        'tuple',
        KApply(
            'abi_type_tuple',
            [
                KApply(
                    'typedArgs',
                    [
                        KApply('abi_type_uint256', [KVariable('V0_x')]),
                        KApply(
                            'typedArgs',
                            [
                                KApply('abi_type_uint256', [KVariable('V1_y')]),
                                KApply(
                                    '.List{"typedArgs"}',
                                ),
                            ],
                        ),
                    ],
                )
            ],
        ),
        None,
        [KEVM.range_uint(256, KVariable('V0_x')), KEVM.range_uint(256, KVariable('V1_y'))],
    ),
    (
        'nested_tuple',
        KApply(
            'abi_type_tuple',
            KApply(
                'typedArgs',
                KApply('abi_type_uint256', [KVariable('V0_x')]),
                KApply(
                    'typedArgs',
                    KApply(
                        'abi_type_tuple',
                        KApply(
                            'typedArgs',
                            KApply('abi_type_uint256', [KVariable('V1_y')]),
                            KApply(
                                '.List{"typedArgs"}',
                            ),
                        ),
                    ),
                    KApply(
                        '.List{"typedArgs"}',
                    ),
                ),
            ),
        ),
        None,
        [KEVM.range_uint(256, KVariable('V0_x')), KEVM.range_uint(256, KVariable('V1_y'))],
    ),
]


@pytest.mark.parametrize(
    'test_id,term,dynamic_type_length,expected',
    PREDICATE_DATA,
    ids=[test_id for test_id, *_ in PREDICATE_DATA],
)
def test_range_predicate(test_id: str, term: KApply, dynamic_type_length: int | None, expected: list[KApply]) -> None:
    # When
    ret = _range_predicates(term, dynamic_type_length)

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
    (
        'full_path',
        'S2K',
        'node_modules%@openzeppelin%contracts%utils%Address',
        'S2KnodeZUndmodulesZModZAtopenzeppelinZModcontractsZModutilsZModAddress',
    ),
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
    ('single_type', Input('RV', 'uint256'), KApply('abi_type_uint256', [KVariable('KV0_RV')])),
    ('underscore_type', Input('_x', 'uint256'), KApply('abi_type_uint256', [KVariable('KV0_x')])),
    ('empty_type', Input('', 'uint256'), KApply('abi_type_uint256', [KVariable('KV0')])),
    (
        'empty_tuple',
        Input('EmptyStruct', 'tuple'),
        KApply('abi_type_tuple', KApply('.List{"typedArgs"}')),
    ),
    (
        'single_tuple',
        Input('SomeStruct', 'tuple', (Input('RV1', 'uint256'), Input('RV2', 'uint256', idx=1))),
        KApply(
            'abi_type_tuple',
            KApply(
                'typedArgs',
                KApply('abi_type_uint256', [KVariable('KV0_RV1')]),
                KApply(
                    'typedArgs',
                    KApply('abi_type_uint256', [KVariable('KV1_RV2')]),
                    KApply(
                        '.List{"typedArgs"}',
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
                'typedArgs',
                KApply('abi_type_uint256', [KVariable('KV0_RV')]),
                KApply(
                    'typedArgs',
                    KApply(
                        'abi_type_tuple',
                        KApply(
                            'typedArgs',
                            KApply('abi_type_uint256', [KVariable('KV1_RV')]),
                            KApply(
                                '.List{"typedArgs"}',
                            ),
                        ),
                    ),
                    KApply(
                        '.List{"typedArgs"}',
                    ),
                ),
            ),
        ),
    ),
]

DEVDOCS_DATA: list[tuple[str, dict, dict, tuple[int, ...] | None, int | None]] = [
    (
        'test_1',
        {
            'kontrol-array-length-equals': {'_withdrawalProof': 10},
            'kontrol-bytes-length-equals': {'_withdrawalProof': 600, 'data': 600},
        },
        {'name': '_withdrawalProof', 'type': 'bytes[]'},
        (10,),
        600,
    ),
    ('test_2', {}, {'name': '_a', 'type': 'bytes'}, None, None),
    (
        'test_3',
        {'kontrol-array-length-equals': {'nestedArray': [10, 10]}, 'kontrol-bytes-length-equals': {'nestedArray': 320}},
        {'name': 'nestedArray', 'type': 'bytes[][][]'},
        (10, 10, 1),
        320,
    ),
]


@pytest.mark.parametrize('test_id,input,expected', INPUT_DATA, ids=[test_id for test_id, *_ in INPUT_DATA])
def test_input_to_abi(test_id: str, input: Input, expected: KApply) -> None:
    # When
    abi = input.to_abi()

    # Then
    assert abi == expected


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
            'internalType': 'struct MyStruct.ComplexType',
            'name': '_tx',
            'type': 'tuple',
        },
        {'kontrol-array-length-equals': {'_v': 10}, 'kontrol-bytes-length-equals': {'_v': 600, 'data': 600}},
        Input(
            name='_tx',
            type='tuple',
            components=(
                Input(
                    name='nonce',
                    type='uint256',
                    internal_type='uint256',
                    components=(),
                    idx=0,
                    array_lengths=None,
                    dynamic_type_length=None,
                ),
                Input(
                    name='sender',
                    type='address',
                    internal_type='address',
                    components=(),
                    idx=1,
                    array_lengths=None,
                    dynamic_type_length=None,
                ),
                Input(
                    name='target',
                    type='address',
                    internal_type='address',
                    components=(),
                    idx=2,
                    array_lengths=None,
                    dynamic_type_length=None,
                ),
                Input(
                    name='value',
                    type='uint256',
                    internal_type='uint256',
                    components=(),
                    idx=3,
                    array_lengths=None,
                    dynamic_type_length=None,
                ),
                Input(
                    name='gasLimit',
                    type='uint256',
                    internal_type='uint256',
                    components=(),
                    idx=4,
                    array_lengths=None,
                    dynamic_type_length=None,
                ),
                Input(
                    name='data',
                    type='bytes',
                    internal_type='bytes',
                    components=(),
                    idx=5,
                    array_lengths=None,
                    dynamic_type_length=600,
                ),
            ),
            idx=0,
            internal_type='struct MyStruct.ComplexType',
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


AST_DATA: list[tuple[str, dict, tuple[StorageField, ...], list[str]]] = [
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
                                        'typeString': 'contract KontrolCheatsBase',
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
        (),
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
        (),
        ['ArithmeticContract.add(uint256,uint256)'],
    ),
    (
        'interface_call',
        {
            'nodeType': 'FunctionDefinition',
            'body': {
                'statements': [
                    {
                        'expression': {
                            'expression': {
                                'expression': {
                                    'name': 'token',
                                    'typeDescriptions': {
                                        'typeIdentifier': 't_contract$_IERC20_$46789',
                                        'typeString': 'contract IERC20',
                                    },
                                },
                                'memberName': 'totalSupply',
                                'nodeType': 'MemberAccess',
                                'typeDescriptions': {
                                    'typeIdentifier': 't_function_external_view$__$returns$_t_uint256_$',
                                    'typeString': 'function () view external returns (uint256)',
                                },
                            },
                            'nodeType': 'FunctionCall',
                        },
                    }
                ],
            },
        },
        (StorageField(label='token', data_type='contract IERC20', slot=0, offset=0, linked_interface='ERC20'),),
        ['ERC20.totalSupply()'],
    ),
    (
        'emit_event',
        {
            'eventCall': {
                'arguments': [],
                'expression': {
                    'argumentTypes': [],
                    'expression': {
                        'typeDescriptions': {
                            'typeIdentifier': 't_type$_t_contract$_IERC20_$40681_$',
                            'typeString': 'type(contract IERC20)',
                        }
                    },
                    'memberName': 'Transfer',
                    'nodeType': 'MemberAccess',
                    'typeDescriptions': {
                        'typeIdentifier': 't_function_event_nonpayable$_t_address_$_t_address_$_t_uint256_$returns$__$',
                        'typeString': 'function (address,address,uint256)',
                    },
                },
                'kind': 'functionCall',
                'nameLocations': [],
                'names': [],
                'nodeType': 'FunctionCall',
                'src': '3625:37:33',
                'typeDescriptions': {'typeIdentifier': 't_tuple$__$', 'typeString': 'tuple()'},
            }
        },
        (),
        [],
    ),
]


@pytest.mark.parametrize(
    'test_id,ast,fields,expected',
    AST_DATA,
    ids=[test_id for test_id, *_ in AST_DATA],
)
def test_find_function_calls(test_id: str, ast: dict, fields: tuple[StorageField, ...], expected: list[str]) -> None:
    # When
    output = find_function_calls(ast, fields)
    # Then
    assert output == expected


LAYOUT_DATA: list[tuple[str, dict, dict, tuple[StorageField, ...]]] = [
    (
        'static-types',
        {
            'storage': [
                {
                    'astId': 46782,
                    'contract': 'src/Counter.sol:Counter',
                    'label': 'x',
                    'offset': 0,
                    'slot': '0',
                    'type': 't_bool',
                },
                {
                    'astId': 46784,
                    'contract': 'src/Counter.sol:Counter',
                    'label': 'secondBoolean',
                    'offset': 1,
                    'slot': '0',
                    'type': 't_bool',
                },
                {
                    'astId': 46786,
                    'contract': 'src/Counter.sol:Counter',
                    'label': 'number',
                    'offset': 0,
                    'slot': '1',
                    'type': 't_uint256',
                },
            ],
            'types': {
                't_bool': {'encoding': 'inplace', 'label': 'bool', 'numberOfBytes': '1'},
                't_uint256': {'encoding': 'inplace', 'label': 'uint256', 'numberOfBytes': '32'},
            },
        },
        {},
        (
            StorageField(label='x', data_type='bool', slot=0, offset=0, linked_interface=None),
            StorageField(label='secondBoolean', data_type='bool', slot=0, offset=1, linked_interface=None),
            StorageField(label='number', data_type='uint256', slot=1, offset=0, linked_interface=None),
        ),
    ),
    (
        'contract-types',
        {
            'storage': [
                {
                    'astId': 46793,
                    'contract': 'test/InterfaceTest.t.sol:InterfaceContract',
                    'label': 'token',
                    'offset': 0,
                    'slot': '0',
                    'type': 't_contract(IERC20)46789',
                },
            ],
            'types': {
                't_contract(IERC20)46789': {'encoding': 'inplace', 'label': 'contract IERC20', 'numberOfBytes': '20'},
            },
        },
        {
            'token': 'ERC20',
        },
        (StorageField(label='token', data_type='contract IERC20', slot=0, offset=0, linked_interface='ERC20'),),
    ),
]


@pytest.mark.parametrize(
    'test_id,storage_layout,interface_annotations,expected',
    LAYOUT_DATA,
    ids=[test_id for test_id, *_ in LAYOUT_DATA],
)
def test_storage_layout_fields(
    test_id: str, storage_layout: dict, interface_annotations: dict, expected: tuple[StorageField, ...]
) -> None:
    # When
    output = process_storage_layout(storage_layout, interface_annotations)
    # Then
    assert output == expected


def test_contract_name_from_bytecode() -> None:
    contract_data: dict[str, tuple[str, list[tuple[int, int]], list[tuple[int, int]]]] = {
        'contract1': ('00000000ffffffffffffffff', [(0, 4)], []),
        'contract2': ('aaaaaaaaaa000000000000aa', [(5, 6)], []),
        'contract3': (
            'bbbbbbbbbbbbbbbbbbbbbb__$53aea86b7d70b31448b230b20ae141a537$__bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            [],
            [(11, 20)],
        ),
    }

    assert (
        _contract_name_from_bytecode(bytecode=bytes.fromhex('ddddddddffffffffffffffff'), contracts=contract_data)
        == 'contract1'
    )
    assert (
        _contract_name_from_bytecode(bytecode=bytes.fromhex('aaaaaaaaaa111111111111aa'), contracts=contract_data)
        == 'contract2'
    )
    assert (
        _contract_name_from_bytecode(
            bytecode=bytes.fromhex(
                'bbbbbbbbbbbbbbbbbbbbbb7777777777777777777777777777777777777777bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
            ),
            contracts=contract_data,
        )
        == 'contract3'
    )


DECODE_DATA: list[tuple[str, KInner, str, dict[bytes, tuple[str, list[str]]], str]] = [
    (
        'concrete-0',
        KToken(
            token='b"\\x08\\xc3y\\xa0\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00 \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\nx is false\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"',
            sort='Bytes',
        ),
        r'b"\x08\xc3y\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\nx is false\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"',
        {},
        'x is false',
    ),
    (
        'concrete-1',
        KToken(
            token='b"\\x05S\\xae\\xd9\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"',
            sort='Bytes',
        ),
        r'b"\x05S\xae\xd9\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"',
        {b'\x05S\xae\xd9': ('TestError', ['uint256', 'bool'])},
        'TestError(0, False)',
    ),
    (
        'symbolic-0',
        KApply(
            label='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
            args=(
                KToken(
                    token='b"\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x12value not accepted\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"',
                    sort='Bytes',
                ),
                KApply(
                    label='String2Bytes(_)_BYTES-HOOKED_Bytes_String',
                    args=(
                        KApply(
                            label='_+String__STRING-COMMON_String_String_String',
                            args=(
                                KApply(
                                    label='_+String__STRING-COMMON_String_String_String',
                                    args=(
                                        KApply(
                                            label='_+String__STRING-COMMON_String_String_String',
                                            args=(
                                                KToken(token='": "', sort='String'),
                                                KApply(
                                                    label='Int2String(_)_STRING-COMMON_String_Int',
                                                    args=(KVariable(name='KV1_foo', sort='Int'),),
                                                ),
                                            ),
                                        ),
                                        KToken(token='" != "', sort='String'),
                                    ),
                                ),
                                KToken(token='"0"', sort='String'),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        r'b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12value not accepted\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" +Bytes String2Bytes ( ": " +String Int2String ( KV1_foo:Int ) +String " != " +String "0" )',
        {},
        'value not accepted `String2Bytes ( ": " +String Int2String ( KV1_foo:Int ) +String " != " +String "0" )`',
    ),
    (
        'symbolic-1',
        KApply(
            label='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
            args=(
                KToken(token='b"\\xd3_E\\xde"', sort='Bytes'),
                KApply(label='buf', args=(KToken(token='32', sort='Int'), KVariable(name='KV0_a', sort='Int'))),
            ),
        ),
        r'b"\xd3_E\xde" +Bytes #buf ( 32 , KV0_a:Int )',
        {b'\xd3_E\xde': ('MyCustomError', ['uint256'])},
        'MyCustomError `#buf ( 32 , KV0_a:Int )`',
    ),
    (
        'symbolic-2',
        KApply(
            label='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
            args=(
                KToken(
                    token='b"\\x08\\xc3y\\xa0\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00 \\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00.a is equal to "',
                    sort='Bytes',
                ),
                KApply(
                    label='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes',
                    args=(
                        KApply(label='buf', args=(KToken(token='32', sort='Int'), KVariable(name='KV0_a', sort='Int'))),
                        KToken(
                            token='b"\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00"',
                            sort='Bytes',
                        ),
                    ),
                ),
            ),
        ),
        r'b"\x08\xc3y\xa0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00.a is equal to " +Bytes #buf ( 32 , KV0_a:Int ) +Bytes b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"',
        {},
        'Error: .a is equal to `#buf ( 32 , KV0_a:Int )`',
    ),
]


@pytest.mark.parametrize(
    'test_id,kinner,kinner_pretty,contract_errors,expected', DECODE_DATA, ids=[test_id for test_id, *_ in DECODE_DATA]
)
def test_decode_kinner_output(
    test_id: str, kinner: KInner, kinner_pretty: str, contract_errors: dict[bytes, tuple[str, list[str]]], expected: str
) -> None:
    output = decode_kinner_output(kinner, kinner_pretty, contract_errors)
    assert output == expected
