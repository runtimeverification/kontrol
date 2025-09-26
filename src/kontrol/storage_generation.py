"""
Storage generation functionality for Kontrol.

This module provides functionality to generate symbolic structured storage constants for Solidity smart contracts based on compilation artifacts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .foundry import Foundry

if TYPE_CHECKING:
    from typing import Final

_LOGGER: Final = logging.getLogger(__name__)


def is_scalar_type(var_type: str) -> bool:
    """Check if a variable type is a scalar type."""
    return (
        var_type == 't_bool'
        or var_type == 't_address'
        or var_type.startswith('t_uint')
        or var_type.startswith('t_enum')
        or var_type.startswith('t_contract')
        or var_type.startswith('t_userDefinedValueType')
    )


def print_constant(name: str, value: int) -> str:
    """Generate a constant declaration string."""
    return f'    uint256 public constant {name} = {value};'


def print_constants_for_storage_variable(prefix: str, slot: int, var: dict[str, Any], types: dict[str, Any]) -> str:
    """Generate constants for a single storage variable."""
    lines = []
    lines.append(print_constant(f'{prefix}_SLOT', slot))
    lines.append(print_constant(f'{prefix}_OFFSET', var['offset']))
    lines.append(print_constant(f'{prefix}_SIZE', types[var['type']]['numberOfBytes']))
    return '\n'.join(lines)


def print_constants_for_storage_variables_recursive(
    prefix: str, slot: int, var: dict[str, Any], types: dict[str, Any]
) -> str:
    """Recursively generate constants for storage variables."""
    lines = []
    updated_prefix = prefix + '_' + var['label'].replace('_', '').upper()
    updated_slot = slot + int(var['slot'])
    var_type = var['type']

    if is_scalar_type(var_type) or var_type.startswith('t_array') or var_type.startswith('t_mapping'):
        lines.append(print_constants_for_storage_variable(updated_prefix, updated_slot, var, types))
    elif var_type.startswith('t_struct'):
        for member in types[var_type]['members']:
            lines.append(print_constants_for_storage_variables_recursive(updated_prefix, updated_slot, member, types))

    return '\n'.join(lines)


def generate_storage_constants(
    contract_name: str, solidity_version: str, storage_data: list[dict[str, Any]], types: dict[str, Any]
) -> str:
    """Generate storage constants library content."""
    lines = []
    lines.append(f'pragma solidity {solidity_version};')
    lines.append('')
    lines.append(f'library {contract_name}StorageConstants {{')

    # Generate constants for storage variables
    for storage_var in storage_data:
        lines.append(print_constants_for_storage_variables_recursive('STORAGE', 0, storage_var, types))

    # Generate constants for struct types
    for var_type in types:
        if var_type.startswith('t_struct'):
            prefix = types[var_type]['label'].replace(' ', '_').replace('.', '_').upper()
            for member in types[var_type]['members']:
                lines.append(print_constants_for_storage_variables_recursive(prefix, 0, member, types))

    lines.append('}')
    return '\n'.join(lines)


def get_storage_layout_from_foundry(
    foundry: Foundry, contract_name: str
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Get storage layout of the specific contract from the Foundry object."""
    # Find the contract in the Foundry object
    contract = None
    for contract_name_with_path, contract_obj in foundry.contracts.items():
        if contract_name_with_path == contract_name.replace('/', '%'):
            contract = contract_obj
            break

    if not contract:
        available_contracts = list(foundry.contracts.keys())
        raise RuntimeError(f'Contract {contract_name} not found in Foundry project. Available contracts: {available_contracts}')

    if not contract.has_storage_layout:
        raise RuntimeError(f'Contract {contract_name} does not have storage layout information')

    # Get storage layout from contract_json
    storage_layout = contract.contract_json.get('storageLayout', {})
    storage = storage_layout.get('storage', [])
    types = storage_layout.get('types', {})

    return contract._name, storage, types
