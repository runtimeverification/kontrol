"""
Unit tests for storage generation functionality.
"""

import json
from pathlib import Path

import pytest

from kontrol.storage_generation import (
    generate_kontrol_test_contract,
    generate_storage_constants,
    is_scalar_type,
    print_constant,
    print_constants_for_storage_variable,
)


class TestStorageGeneration:
    """Test cases for storage generation functionality."""

    def test_is_scalar_type(self):
        """Test scalar type detection."""
        assert is_scalar_type('t_bool')
        assert is_scalar_type('t_address')
        assert is_scalar_type('t_uint256')
        assert is_scalar_type('t_enum')
        assert is_scalar_type('t_contract')
        assert is_scalar_type('t_userDefinedValueType')
        
        assert not is_scalar_type('t_struct')
        assert not is_scalar_type('t_array')
        assert not is_scalar_type('t_mapping')

    def test_print_constant(self):
        """Test constant generation."""
        result = print_constant('TEST_CONSTANT', 42)
        expected = '    uint256 public constant TEST_CONSTANT = 42;'
        assert result == expected

    def test_print_constants_for_storage_variable(self):
        """Test storage variable constant generation."""
        var = {'offset': 0, 'type': 't_uint256'}
        types = {'t_uint256': {'numberOfBytes': 32}}
        
        result = print_constants_for_storage_variable('TEST', 0, var, types)
        lines = result.split('\n')
        
        assert '    uint256 public constant TEST_SLOT = 0;' in lines
        assert '    uint256 public constant TEST_OFFSET = 0;' in lines
        assert '    uint256 public constant TEST_SIZE = 32;' in lines

    def test_generate_storage_constants(self):
        """Test storage constants library generation."""
        storage_data = {
            'storage': [
                {
                    'label': 'totalSupply',
                    'offset': 0,
                    'slot': 0,
                    'type': 't_uint256'
                }
            ]
        }
        types = {
            't_uint256': {'numberOfBytes': 32}
        }
        
        result = generate_storage_constants('TestContract', '0.8.26', storage_data, types)
        
        assert 'pragma solidity 0.8.26;' in result
        assert 'library TestContractStorageConstants {' in result
        assert 'STORAGE_TOTALSUPPLY_SLOT' in result
        assert 'STORAGE_TOTALSUPPLY_OFFSET' in result
        assert 'STORAGE_TOTALSUPPLY_SIZE' in result

    def test_generate_kontrol_test_contract(self):
        """Test KontrolTest contract generation."""
        result = generate_kontrol_test_contract('0.8.26')
        
        assert 'pragma solidity 0.8.26;' in result
        assert 'contract KontrolTest is Test, KontrolCheats {' in result
        assert 'function _loadData(' in result
        assert 'function _storeData(' in result
        assert 'function _loadMappingData(' in result
        assert 'function _storeMappingData(' in result
        assert 'function _assumeNoOverflow(' in result
        assert 'function _clearSlot(' in result
        assert 'function _clearMappingSlot(' in result

    def test_generate_storage_constants_with_struct(self):
        """Test storage constants generation with struct types."""
        storage_data = {
            'storage': [
                {
                    'label': 'user',
                    'offset': 0,
                    'slot': 0,
                    'type': 't_struct_User'
                }
            ]
        }
        types = {
            't_struct_User': {
                'label': 'User',
                'members': [
                    {
                        'label': 'balance',
                        'offset': 0,
                        'slot': 0,
                        'type': 't_uint256'
                    },
                    {
                        'label': 'active',
                        'offset': 32,
                        'slot': 0,
                        'type': 't_bool'
                    }
                ]
            },
            't_uint256': {'numberOfBytes': 32},
            't_bool': {'numberOfBytes': 1}
        }
        
        result = generate_storage_constants('TestContract', '0.8.26', storage_data, types)
        
        # Check that struct member constants are generated
        assert 'USER_BALANCE_SLOT' in result
        assert 'USER_BALANCE_OFFSET' in result
        assert 'USER_BALANCE_SIZE' in result
        assert 'USER_ACTIVE_SLOT' in result
        assert 'USER_ACTIVE_OFFSET' in result
        assert 'USER_ACTIVE_SIZE' in result
