"""
Integration tests for storage generation functionality.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from kontrol.foundry import Foundry
from kontrol.storage_generation import foundry_storage_generation
from kontrol.options import StorageGenerationOptions


class TestStorageGenerationIntegration:
    """Integration tests for storage generation functionality."""

    def test_storage_generation_with_simple_contract(self):
        """Test storage generation with a simple contract."""
        # Create a temporary directory for the test
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a simple Solidity contract
            contract_content = '''
pragma solidity 0.8.26;

contract SimpleStorage {
    uint256 public totalSupply;
    mapping(address => uint256) public balances;
    
    struct User {
        uint256 balance;
        bool active;
    }
    
    User public user;
    
    constructor() {
        totalSupply = 1000;
    }
    
    function setBalance(address account, uint256 amount) public {
        balances[account] = amount;
    }
}
'''
            
            # Create the contract file
            src_dir = temp_path / 'src'
            src_dir.mkdir()
            contract_file = src_dir / 'SimpleStorage.sol'
            contract_file.write_text(contract_content)
            
            # Create foundry.toml
            foundry_toml = temp_path / 'foundry.toml'
            foundry_toml.write_text('''
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.26"
''')
            
            # Initialize foundry
            foundry = Foundry(foundry_root=temp_path)
            
            # Create options for storage generation
            options = StorageGenerationOptions({
                'contract_name': 'SimpleStorage',
                'solidity_version': '0.8.26',
                'output_file': None,
                'test_contract': True,
                'foundry_root': temp_path,
                'enum_constraints': False,
            })
            
            # Run symbolic storage setup
            foundry_storage_generation(foundry=foundry, options=options)
            
            # Check that files were generated
            storage_constants_file = temp_path / 'test' / 'kontrol' / 'storage' / 'SimpleStorageStorageConstants.sol'
            assert storage_constants_file.exists()
            
            kontrol_test_file = temp_path / 'test' / 'kontrol' / 'KontrolTest.sol'
            assert kontrol_test_file.exists()
            
            # Check content of generated files
            storage_content = storage_constants_file.read_text()
            assert 'library SimpleStorageStorageConstants {' in storage_content
            assert 'STORAGE_TOTALSUPPLY_SLOT' in storage_content
            assert 'STORAGE_BALANCES_SLOT' in storage_content
            assert 'STORAGE_USER_SLOT' in storage_content
            
            test_content = kontrol_test_file.read_text()
            assert 'contract KontrolTest is Test, KontrolCheats {' in test_content
            assert 'function _loadData(' in test_content
            assert 'function _storeData(' in test_content

    def test_storage_generation_with_custom_output(self):
        """Test storage generation with custom output file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a simple contract
            contract_content = '''
pragma solidity 0.8.26;

contract TestContract {
    uint256 public value;
}
'''
            
            src_dir = temp_path / 'src'
            src_dir.mkdir()
            contract_file = src_dir / 'TestContract.sol'
            contract_file.write_text(contract_content)
            
            # Create foundry.toml
            foundry_toml = temp_path / 'foundry.toml'
            foundry_toml.write_text('''
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.26"
''')
            
            foundry = Foundry(foundry_root=temp_path)
            
            # Test with custom output file
            custom_output = temp_path / 'custom_storage.sol'
            options = StorageGenerationOptions({
                'contract_name': 'TestContract',
                'solidity_version': '0.8.26',
                'output_file': str(custom_output),
                'test_contract': False,
                'foundry_root': temp_path,
                'enum_constraints': False,
            })
            
            foundry_storage_generation(foundry=foundry, options=options)
            
            # Check that custom output file was created
            assert custom_output.exists()
            
            content = custom_output.read_text()
            assert 'library TestContractStorageConstants {' in content
            assert 'STORAGE_VALUE_SLOT' in content
