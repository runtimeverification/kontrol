from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from kontrol.storage_generation import (
    generate_storage_constants,
    is_scalar_type,
    print_constant,
    print_constants_for_storage_variables_recursive,
)

if TYPE_CHECKING:
    from typing import Final

# Test data
SCALAR_TYPE_TEST_DATA: Final = [
    ('t_bool', True),
    ('t_address', True),
    ('t_uint256', True),
    ('t_enum_Status', True),
    ('t_contract_MyContract', True),
    ('t_userDefinedValueType_MyType', True),
    ('t_array_fixed', False),
    ('t_mapping', False),
    ('t_struct_Data', False),
]

CONSTANT_TEST_DATA: Final = [
    ('TEST_CONSTANT', 42, '    uint256 public constant TEST_CONSTANT = 42;'),
    ('STORAGE_SLOT', 0, '    uint256 public constant STORAGE_SLOT = 0;'),
    ('SIZE_BYTES', 32, '    uint256 public constant SIZE_BYTES = 32;'),
]

SIMPLE_STORAGE_DATA: Final = [
    {
        'label': 'number',
        'type': 't_uint256',
        'slot': '0',
        'offset': 0,
    }
]

SIMPLE_TYPES: Final = {
    't_uint256': {
        'label': 'uint256',
        'numberOfBytes': 32,
    }
}

COMPLEX_STORAGE_DATA: Final = [
    {
        'label': 'owner',
        'type': 't_address',
        'slot': '0',
        'offset': 0,
    },
    {
        'label': 'balance',
        'type': 't_uint256',
        'slot': '1',
        'offset': 0,
    },
    {
        'label': 'data',
        'type': 't_struct_Data',
        'slot': '2',
        'offset': 0,
    },
]

COMPLEX_TYPES: Final = {
    't_address': {
        'label': 'address',
        'numberOfBytes': 20,
    },
    't_uint256': {
        'label': 'uint256',
        'numberOfBytes': 32,
    },
    't_struct_Data': {
        'label': 'Data',
        'numberOfBytes': 64,
        'members': [
            {
                'label': 'value',
                'type': 't_uint256',
                'slot': '0',
                'offset': 0,
            },
            {
                'label': 'flag',
                'type': 't_bool',
                'slot': '1',
                'offset': 0,
            },
        ],
    },
    't_bool': {
        'label': 'bool',
        'numberOfBytes': 1,
    },
}

STORAGE_VARIABLE_TEST_DATA: Final = [
    (
        'uint256',
        'STORAGE',
        0,
        SIMPLE_STORAGE_DATA[0],
        SIMPLE_TYPES,
        """    uint256 public constant STORAGE_NUMBER_SLOT = 0;
    uint256 public constant STORAGE_NUMBER_OFFSET = 0;
    uint256 public constant STORAGE_NUMBER_SIZE = 32;""",
    ),
    (
        'address',
        'STORAGE',
        0,
        {'label': 'owner', 'type': 't_address', 'slot': '0', 'offset': 0},
        {'t_address': {'label': 'address', 'numberOfBytes': 20}},
        """    uint256 public constant STORAGE_OWNER_SLOT = 0;
    uint256 public constant STORAGE_OWNER_OFFSET = 0;
    uint256 public constant STORAGE_OWNER_SIZE = 20;""",
    ),
]

STORAGE_CONSTANTS_TEST_DATA: Final = [
    (
        'simple',
        'Counter',
        '0.8.26',
        SIMPLE_STORAGE_DATA,
        SIMPLE_TYPES,
        [
            'pragma solidity 0.8.26;',
            'library CounterStorageConstants {',
            'uint256 public constant STORAGE_NUMBER_SLOT = 0;',
            'uint256 public constant STORAGE_NUMBER_OFFSET = 0;',
            'uint256 public constant STORAGE_NUMBER_SIZE = 32;',
        ],
    ),
    (
        'complex',
        'ComplexContract',
        '0.8.24',
        COMPLEX_STORAGE_DATA,
        COMPLEX_TYPES,
        [
            'pragma solidity 0.8.24;',
            'library ComplexContractStorageConstants {',
            'uint256 public constant STORAGE_OWNER_SLOT = 0;',
            'uint256 public constant STORAGE_BALANCE_SLOT = 1;',
            'uint256 public constant STORAGE_DATA_VALUE_SLOT = 2;',
            'uint256 public constant STORAGE_DATA_FLAG_SLOT = 3;',
            'uint256 public constant DATA_VALUE_SLOT = 0;',
            'uint256 public constant DATA_FLAG_SLOT = 1;',
        ],
    ),
    (
        'empty',
        'EmptyContract',
        '0.8.26',
        [],
        {},
        ['pragma solidity 0.8.26;', 'library EmptyContractStorageConstants {', '}'],
    ),
]


class TestStorageGeneration:
    """Test cases for storage generation functionality."""

    @pytest.mark.parametrize(
        'var_type,expected', SCALAR_TYPE_TEST_DATA, ids=[test_id for test_id, *_ in SCALAR_TYPE_TEST_DATA]
    )
    def test_is_scalar_type(self, var_type: str, expected: bool) -> None:
        """Test scalar type detection."""
        assert is_scalar_type(var_type) == expected

    @pytest.mark.parametrize(
        'name,value,expected', CONSTANT_TEST_DATA, ids=[test_id for test_id, *_ in CONSTANT_TEST_DATA]
    )
    def test_print_constant(self, name: str, value: int, expected: str) -> None:
        """Test constant generation."""
        result = print_constant(name, value)
        assert result == expected

    @pytest.mark.parametrize(
        'test_id,prefix,slot,var,types,expected',
        STORAGE_VARIABLE_TEST_DATA,
        ids=[test_id for test_id, *_ in STORAGE_VARIABLE_TEST_DATA],
    )
    def test_print_constants_for_storage_variables_recursive(
        self, test_id: str, prefix: str, slot: int, var: dict[str, Any], types: dict[str, Any], expected: str
    ) -> None:
        """Test recursive constants generation for storage variables."""
        result = print_constants_for_storage_variables_recursive(prefix, slot, var, types)
        assert result == expected

    @pytest.mark.parametrize(
        'test_id,contract_name,solidity_version,storage_data,types,expected_strings',
        STORAGE_CONSTANTS_TEST_DATA,
        ids=[test_id for test_id, *_ in STORAGE_CONSTANTS_TEST_DATA],
    )
    def test_generate_storage_constants(
        self,
        test_id: str,
        contract_name: str,
        solidity_version: str,
        storage_data: list[dict[str, Any]],
        types: dict[str, Any],
        expected_strings: list[str],
    ) -> None:
        """Test storage constants generation for various contract types."""
        result = generate_storage_constants(contract_name, solidity_version, storage_data, types)

        for expected_string in expected_strings:
            assert expected_string in result
