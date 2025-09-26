from __future__ import annotations

import sys
from pathlib import Path

import pytest

from kontrol.foundry import Foundry, foundry_storage_generation
from kontrol.options import SetupSymbolicStorageOptions

sys.setrecursionlimit(10**7)


def test_setup_symbolic_storage(foundry: Foundry) -> None:
    """Test the setup-symbolic-storage command with Token contract."""
    options = SetupSymbolicStorageOptions(
        {
            'contract_names': ['src%Token'],
            'solidity_version': '0.8.26',
            'output_file': None,
            'foundry_root': foundry._root,
            'enum_constraints': False,
            'log_level': 'INFO',
        }
    )

    foundry_storage_generation(foundry, options)

    # Check that output file was created
    token_file = foundry._root / 'test' / 'kontrol' / 'storage' / 'TokenStorageConstants.sol'

    assert token_file.exists(), f"Token file not created: {token_file}"

    # Check Token content
    token_content = token_file.read_text()
    assert 'library TokenStorageConstants {' in token_content
    assert 'uint256 public constant STORAGE_X_SLOT' in token_content
    assert 'uint256 public constant STORAGE_BALANCES_SLOT' in token_content
    assert 'uint256 public constant STORAGE_ALLOWANCES_SLOT' in token_content
    assert 'uint256 public constant STORAGE_Y_SLOT' in token_content
    assert 'uint256 public constant STORAGE_Z_SLOT' in token_content
    assert 'uint256 public constant STORAGE_A_SLOT' in token_content
    assert 'uint256 public constant STORAGE_FOOS_SLOT' in token_content
    assert 'uint256 public constant STRUCT_TOKEN_FOO_BAR_SLOT' in token_content