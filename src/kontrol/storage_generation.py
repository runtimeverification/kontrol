"""
Storage generation functionality for Kontrol.

This module provides functionality to generate symbolic structured storage constants for Solidity smart contracts based on compilation artifacts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import Final

    from .foundry import Foundry

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
        raise RuntimeError(
            f'Contract {contract_name} not found in Foundry project. Available contracts: {available_contracts}'
        )

    if not contract.has_storage_layout:
        raise RuntimeError(f'Contract {contract_name} does not have storage layout information')

    # Get storage layout from contract_json
    storage_layout = contract.contract_json.get('storageLayout', {})
    storage = storage_layout.get('storage', [])
    types = storage_layout.get('types', {})

    return contract._name, storage, types


def generate_setup_contract(
    contract_name: str,
    solidity_version: str,
    storage: list[dict[str, Any]],
    types: dict[str, Any],
) -> str:
    """Generate a setup contract for symbolic storage initialization."""

    # Generate imports
    imports = _generate_imports(contract_name, solidity_version)

    # Generate contract declaration
    contract_declaration = _generate_contract_declaration(contract_name)

    # Generate storage constants
    storage_constants = _generate_storage_constants(contract_name, storage, types)

    # Generate main setup function
    setup_function = _generate_main_setup_function(contract_name, storage, types)

    return f"""{imports}

{contract_declaration}
{storage_constants}

{setup_function}
}}"""


def _generate_imports(contract_name: str, solidity_version: str) -> str:
    """Generate import statements for the setup contract."""
    return f"""pragma solidity {solidity_version};

import {{{contract_name}}} from "src/{contract_name}.sol";
import {{KontrolTest}} from "test/kontrol/KontrolTest.sol";
import {{{contract_name}StorageConstants}} from "test/kontrol/storage/{contract_name}StorageConstants.sol";"""


def _generate_contract_declaration(contract_name: str) -> str:
    """Generate the contract declaration."""
    return f"""contract {contract_name}StorageSetup is KontrolTest {{"""


def _generate_storage_constants(contract_name: str, storage: list[dict[str, Any]], types: dict[str, Any]) -> str:
    """Generate storage constant declarations."""
    # Import all constants from the storage constants library
    return f'    // All storage constants are imported from {contract_name}StorageConstants'


# TODO: Add auxiliary functions for complex storage patterns (mappings, arrays, structs)
# This would include functions like:
# - _setupMappingData for mappings
# - _setupArrayData for arrays


def _generate_main_setup_function(contract_name: str, storage: list[dict[str, Any]], types: dict[str, Any]) -> str:
    """Generate the main setup function."""
    function_name = f'{contract_name[0].lower() + contract_name[1:]}StorageSetup'

    # Generate function signature with parameters
    supported_fields = []
    unsupported_fields = []

    for field in storage:
        type_name = types[field['type']]['label']
        if _is_supported_type(type_name):
            supported_fields.append(field)
        else:
            unsupported_fields.append((field['label'], type_name))

    # Build parameter list
    params = ['address _contractAddress']
    for field in supported_fields:
        field_name = field['label']
        type_name = types[field['type']]['label']

        if type_name.startswith('struct '):
            # For structs, add parameters for each member
            struct_type_id = field['type']
            if struct_type_id in types and 'members' in types[struct_type_id]:
                for member in types[struct_type_id]['members']:
                    member_type = types[member['type']]['label']
                    if _is_supported_type(member_type):
                        param_type = _get_solidity_type_name(member_type, types)
                        params.append(f'{param_type} _{field_name}_{member["label"]}')
        else:
            # For basic types
            param_type = _get_solidity_type_name(type_name, types)
            params.append(f'{param_type} _{field_name}')

    lines = [
        f'    function {function_name}({", ".join(params)}) public {{',
        '        vm.setArbitraryStorage(_contractAddress);',
        '',
    ]

    # Track which slots have been cleared to avoid clearing the same slot multiple times
    cleared_slots = set()

    # Generate storage assignments
    for field in supported_fields:
        field_name = field['label']
        type_name = types[field['type']]['label']
        slot = field['slot']

        if type_name.startswith('struct '):
            # For structs, handle each member separately
            struct_type_id = field['type']
            if struct_type_id in types and 'members' in types[struct_type_id]:
                for member in types[struct_type_id]['members']:
                    member_type = types[member['type']]['label']
                    if _is_supported_type(member_type):
                        member_slot = int(member['slot'])

                        # Clear slot if not already cleared
                        if member_slot not in cleared_slots:
                            storage_prefix = f'STORAGE_{field_name.upper()}'
                            lines.append(
                                f'        _clearSlot(_contractAddress, {contract_name}StorageConstants.{storage_prefix}_{member["label"].upper()}_SLOT);'
                            )
                            cleared_slots.add(member_slot)

                        # Generate storage assignment for struct member
                        storage_code = _generate_struct_member_storage_assignment(
                            field_name, member, member_type, contract_name, types[struct_type_id]
                        )
                        lines.append(f'        {storage_code}')
                        lines.append('')
        else:
            # For basic types
            # Clear slot if not already cleared (multiple variables can share the same slot)
            if slot not in cleared_slots:
                lines.append(
                    f'        _clearSlot(_contractAddress, {contract_name}StorageConstants.STORAGE_{field_name.upper()}_SLOT);'
                )
                cleared_slots.add(slot)

            # Generate storage assignment using parameter
            storage_code = _generate_storage_assignment_with_param(field_name, type_name, contract_name)
            lines.append(f'        {storage_code}')
            lines.append('')

    # Add TODO comment for unsupported types
    if unsupported_fields:
        lines.append('        // TODO: Add support for the following types:')
        for field_name, type_name in unsupported_fields:
            lines.append(f'        // - {type_name} {field_name}')
        lines.append('')

    lines.append('    }')

    return '\n'.join(lines)


def _is_supported_type(type_name: str) -> bool:
    """Check if a type is supported for symbolic storage generation."""
    if type_name.endswith('[]'):
        # TODO: Add support for arrays
        return False

    # Basic supported types
    if type_name in {'address', 'bool', 'bytes32'} or type_name.startswith(('uint', 'int')):
        return True

    # Structs are supported since they are stored directly in storage
    if type_name.startswith('struct '):
        return True

    return False


def _get_solidity_type_name(type_name: str, types: dict[str, Any] | None = None) -> str:
    """Get the Solidity type name for a field type."""
    if type_name in {'address', 'bool', 'bytes32'}:
        return type_name

    # For uint/int, use actual bit size from storage layout
    if type_name.startswith(('uint', 'int')):
        if types and type_name in types:
            bit_size = types[type_name].get('numberOfBytes', 0) * 8
            if 1 <= bit_size <= 256 and bit_size % 8 == 0:
                if type_name.startswith('uint'):
                    return f'uint{bit_size}'
                else:  # int
                    return f'int{bit_size}'

        # Fallback to original type name if we can't determine bit size
        return type_name

    # Fallback
    return 'uint256'


def _generate_storage_assignment_with_param(field_name: str, type_name: str, contract_name: str) -> str:
    """Generate storage assignment for a field using a parameter."""
    # Generate the appropriate conversion based on type
    conversion = _get_type_conversion(f'_{field_name}', type_name)

    return f'_storeData(_contractAddress, {contract_name}StorageConstants.STORAGE_{field_name.upper()}_SLOT, {contract_name}StorageConstants.STORAGE_{field_name.upper()}_OFFSET, {contract_name}StorageConstants.STORAGE_{field_name.upper()}_SIZE, {conversion});'


def _generate_struct_member_storage_assignment(
    field_name: str, member: dict[str, Any], member_type: str, contract_name: str, struct_type: dict[str, Any]
) -> str:
    """Generate storage assignment for a struct member using a parameter."""
    # Generate the appropriate conversion based on type
    param_name = f'_{field_name}_{member["label"]}'
    conversion = _get_type_conversion(param_name, member_type)

    # Use the storage field prefix, not the struct type prefix
    storage_prefix = f'STORAGE_{field_name.upper()}'

    return f'_storeData(_contractAddress, {contract_name}StorageConstants.{storage_prefix}_{member["label"].upper()}_SLOT, {contract_name}StorageConstants.{storage_prefix}_{member["label"].upper()}_OFFSET, {contract_name}StorageConstants.{storage_prefix}_{member["label"].upper()}_SIZE, {conversion});'


def _get_type_conversion(field_name: str, type_name: str) -> str:
    """Get the appropriate type conversion for storage assignment."""
    if type_name == 'uint256' or type_name == 'uint':
        return field_name
    elif type_name == 'address':
        return f'uint160({field_name})'
    elif type_name == 'bool':
        return f'boolToUint256({field_name})'
    elif type_name.startswith('uint'):
        # cast to uint256
        return f'uint256({field_name})'
    elif type_name.startswith('int'):
        # convert to int256 to handle sign extension, then to uint256
        return f'uint256(int256({field_name}))'
    elif type_name == 'bytes32':
        return f'uint256({field_name})'
    else:
        # This should not happen since we filter unsupported types
        raise ValueError(f'Unsupported type {type_name} should have been filtered out')
