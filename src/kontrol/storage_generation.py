"""
Storage generation functionality for Kontrol.

This module provides functionality to generate symbolic structured storage constants
and test contracts for Solidity smart contracts based on Foundry storage inspection.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .foundry import Foundry
from .options import StorageGenerationOptions
from .utils import console


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
    contract_name: str, solidity_version: str, storage_data: dict[str, Any], types: dict[str, Any]
) -> str:
    """Generate storage constants library content."""
    lines = []
    lines.append(f'pragma solidity {solidity_version};')
    lines.append('')
    lines.append(f'library {contract_name}StorageConstants {{')

    # Generate constants for storage variables
    for storage_var in storage_data['storage']:
        lines.append(print_constants_for_storage_variables_recursive('STORAGE', 0, storage_var, types))

    # Generate constants for struct types
    for var_type in types:
        if var_type.startswith('t_struct'):
            prefix = types[var_type]['label'].replace(' ', '_').replace('.', '_').upper()
            for member in types[var_type]['members']:
                lines.append(print_constants_for_storage_variables_recursive(prefix, 0, member, types))

    lines.append('}')
    return '\n'.join(lines)


def generate_storage_setup_function(contract_name: str, storage_data: dict[str, Any], types: dict[str, Any]) -> str:
    """Generate a setUp function that initializes all storage variables symbolically."""
    lines = []
    lines.append(f'    function setUp{contract_name}Storage({contract_name} _{contract_name.lower()}) internal {{')
    lines.append(f'        kevm.symbolicStorage(address(_{contract_name.lower()}));')
    lines.append('')
    
    # Generate setup for each storage variable
    for storage_var in storage_data['storage']:
        var_name = storage_var['label']
        var_type = storage_var['type']
        
        if is_scalar_type(var_type):
            # Generate symbolic value for scalar types
            lines.append(f'        // Setup {var_name} ({var_type})')
            lines.append(f'        uint256 {var_name}_value = freshUInt256("{var_name}");')
            
            # Add constraints based on type
            if var_type == 't_bool':
                lines.append(f'        vm.assume({var_name}_value <= 1);')
            elif var_type.startswith('t_uint'):
                # Extract bit width from type
                if '8' in var_type:
                    lines.append(f'        vm.assume({var_name}_value < 2**8);')
                elif '16' in var_type:
                    lines.append(f'        vm.assume({var_name}_value < 2**16);')
                elif '32' in var_type:
                    lines.append(f'        vm.assume({var_name}_value < 2**32);')
                elif '64' in var_type:
                    lines.append(f'        vm.assume({var_name}_value < 2**64);')
                elif '128' in var_type:
                    lines.append(f'        vm.assume({var_name}_value < 2**128);')
                # For uint256, no constraint needed
            
            lines.append(f'        _storeData(')
            lines.append(f'            address(_{contract_name.lower()}),')
            lines.append(f'            {contract_name}StorageConstants.STORAGE_{var_name.upper()}_SLOT,')
            lines.append(f'            {contract_name}StorageConstants.STORAGE_{var_name.upper()}_OFFSET,')
            lines.append(f'            {contract_name}StorageConstants.STORAGE_{var_name.upper()}_SIZE,')
            lines.append(f'            {var_name}_value')
            lines.append(f'        );')
            lines.append('')
            
        elif var_type.startswith('t_mapping'):
            lines.append(f'        // Setup {var_name} (mapping) - will be populated as needed')
            lines.append(f'        // Use _storeMappingData() for specific key-value pairs')
            lines.append('')
            
        elif var_type.startswith('t_struct'):
            lines.append(f'        // Setup {var_name} (struct) - individual members will be set below')
            lines.append('')
            # Generate setup for struct members
            struct_type = types[var_type]
            for member in struct_type['members']:
                member_name = member['label']
                member_type = member['type']
                if is_scalar_type(member_type):
                    lines.append(f'        // Setup {var_name}.{member_name} ({member_type})')
                    lines.append(f'        uint256 {var_name}_{member_name}_value = freshUInt256("{var_name}_{member_name}");')
                    
                    if member_type == 't_bool':
                        lines.append(f'        vm.assume({var_name}_{member_name}_value <= 1);')
                    elif member_type.startswith('t_uint'):
                        if '8' in member_type:
                            lines.append(f'        vm.assume({var_name}_{member_name}_value < 2**8);')
                        elif '16' in member_type:
                            lines.append(f'        vm.assume({var_name}_{member_name}_value < 2**16);')
                        elif '32' in member_type:
                            lines.append(f'        vm.assume({var_name}_{member_name}_value < 2**32);')
                        elif '64' in member_type:
                            lines.append(f'        vm.assume({var_name}_{member_name}_value < 2**64);')
                        elif '128' in member_type:
                            lines.append(f'        vm.assume({var_name}_{member_name}_value < 2**128);')
                    
                    lines.append(f'        _storeData(')
                    lines.append(f'            address(_{contract_name.lower()}),')
                    lines.append(f'            {contract_name}StorageConstants.{var_name.upper()}_{member_name.upper()}_SLOT,')
                    lines.append(f'            {contract_name}StorageConstants.{var_name.upper()}_{member_name.upper()}_OFFSET,')
                    lines.append(f'            {contract_name}StorageConstants.{var_name.upper()}_{member_name.upper()}_SIZE,')
                    lines.append(f'            {var_name}_{member_name}_value')
                    lines.append(f'        );')
                    lines.append('')
    
    lines.append('    }')
    return '\n'.join(lines)


def generate_complete_test_contract(
    contract_name: str, solidity_version: str, storage_data: dict[str, Any], types: dict[str, Any]
) -> str:
    """Generate a complete test contract with setUp function."""
    lines = []
    lines.append(f'pragma solidity {solidity_version};')
    lines.append('')
    lines.append(f'import "contracts/{contract_name}.sol";')
    lines.append('import "test/kontrol/KontrolTest.sol";')
    lines.append(f'import "test/kontrol/storage/{contract_name}StorageConstants.sol";')
    lines.append('')
    lines.append(f'contract {contract_name}Test is KontrolTest {{')
    lines.append('')
    
    # Add the storage setup function
    lines.append(generate_storage_setup_function(contract_name, storage_data, types))
    lines.append('')
    
    # Add a sample test function
    lines.append(f'    function test{contract_name}Symbolic() external {{')
    lines.append(f'        {contract_name} contract = new {contract_name}();')
    lines.append(f'        setUp{contract_name}Storage(contract);')
    lines.append('        ')
    lines.append('        // Your test logic here')
    lines.append('        // The contract storage is now set up with symbolic values')
    lines.append('        // that can be used for formal verification')
    lines.append('    }')
    lines.append('}')
    
    return '\n'.join(lines)


def generate_kontrol_test_contract(solidity_version: str) -> str:
    """Generate the KontrolTest base contract."""
    return f'''pragma solidity {solidity_version};

import "forge-std/Vm.sol";
import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract KontrolTest is Test, KontrolCheats {{
    function infoAssert(bool condition, string memory message) external {{
        if (!condition) {{
            revert(message);
        }}
    }}

    enum Mode {{
        Assume,
        Try,
        Assert
    }}

    function _establish(Mode mode, bool condition) internal pure returns (bool) {{
        if (mode == Mode.Assume) {{
            vm.assume(condition);
            return true;
        }} else if (mode == Mode.Try) {{
            return condition;
        }} else {{
            assert(condition);
            return true;
        }}
    }}

    function _loadData(
        address contractAddress,
        uint256 slot,
        uint256 offset,
        uint256 width
    ) internal view returns (uint256) {{
        // `offset` and `width` must not overflow the slot
        assert(offset + width <= 32);

        // Slot read mask
        uint256 mask;
        unchecked {{
            mask = (2 ** (8 * width)) - 1;
        }}
        // Value right shift
        uint256 shift = 8 * offset;

        // Current slot value
        uint256 slotValue = uint256(vm.load(contractAddress, bytes32(slot)));

        // Isolate and return data to retrieve
        return mask & (slotValue >> shift);
    }}

    function _storeData(address contractAddress, uint256 slot, uint256 offset, uint256 width, uint256 value) internal {{
        // `offset` and `width` must not overflow the slot
        assert(offset + width <= 32);
        // and `value` must fit into the designated part
        assert(width == 32 || value < 2 ** (8 * width));

        // Slot update mask
        uint256 maskLeft;
        unchecked {{
            maskLeft = ~((2 ** (8 * (offset + width))) - 1);
        }}
        uint256 maskRight = (2 ** (8 * offset)) - 1;
        uint256 mask = maskLeft | maskRight;

        uint256 value = (2 ** (8 * offset)) * value;

        // Current slot value
        uint256 slotValue = uint256(vm.load(contractAddress, bytes32(slot)));
        // Updated slot value
        slotValue = value | (mask & slotValue);

        vm.store(contractAddress, bytes32(slot), bytes32(slotValue));
    }}

    function _loadMappingData(
        address contractAddress,
        uint256 mappingSlot,
        uint256 key,
        uint256 subSlot,
        uint256 offset,
        uint256 width
    ) internal view returns (uint256) {{
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        return _loadData(contractAddress, uint256(hashedSlot) + subSlot, offset, width);
    }}

    function _storeMappingData(
        address contractAddress,
        uint256 mappingSlot,
        uint256 key,
        uint256 subSlot,
        uint256 offset,
        uint256 width,
        uint256 value
    ) internal {{
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        _storeData(contractAddress, uint256(hashedSlot) + subSlot, offset, width, value);
    }}

    function _loadUInt256(address contractAddress, uint256 slot) internal view returns (uint256) {{
        return _loadData(contractAddress, slot, 0, 32);
    }}

    function _loadMappingUInt256(
        address contractAddress,
        uint256 mappingSlot,
        uint256 key,
        uint256 subSlot
    ) internal view returns (uint256) {{
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        return _loadData(contractAddress, uint256(hashedSlot) + subSlot, 0, 32);
    }}

    function _loadAddress(address contractAddress, uint256 slot) internal view returns (address) {{
        return address(uint160(_loadData(contractAddress, slot, 0, 20)));
    }}

    function _storeMappingUInt256(
        address contractAddress,
        uint256 mappingSlot,
        uint256 key,
        uint256 subSlot,
        uint256 value
    ) internal {{
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        _storeData(contractAddress, uint256(hashedSlot) + subSlot, 0, 32, value);
    }}

    function _storeUInt256(address contractAddress, uint256 slot, uint256 value) internal {{
        _storeData(contractAddress, slot, 0, 32, value);
    }}

    function _storeAddress(address contractAddress, uint256 slot, address value) internal {{
        _storeData(contractAddress, slot, 0, 20, uint160(value));
    }}

    function _storeBytes32(address contractAddress, uint256 slot, bytes32 value) internal {{
        _storeUInt256(contractAddress, slot, uint256(value));
    }}

    function _assumeNoOverflow(uint256 augend, uint256 addend) internal {{
        unchecked {{
            vm.assume(augend < augend + addend);
        }}
    }}

    function _clearSlot(address contractAddress, uint256 slot) internal {{
        _storeUInt256(contractAddress, slot, 0);
    }}

    function _clearMappingSlot(address contractAddress, uint256 mappingSlot, uint256 key, uint256 subSlot) internal {{
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        _storeData(contractAddress, uint256(hashedSlot) + subSlot, 0, 32, 0);
    }}
}}'''


def run_forge_inspect(foundry: Foundry, contract_name: str) -> dict[str, Any]:
    """Run forge inspect to get storage layout for a contract."""
    try:
        result = subprocess.run(
            ['forge', 'inspect', contract_name, 'storage', '--json'],
            cwd=foundry._root,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        console.print(f'[bold red]Error running forge inspect:[/bold red] {e.stderr}')
        sys.exit(1)
    except json.JSONDecodeError as e:
        console.print(f'[bold red]Error parsing forge inspect output:[/bold red] {e}')
        sys.exit(1)


def foundry_storage_generation(foundry: Foundry, options: StorageGenerationOptions) -> None:
    """Generate storage constants and test contracts for a given contract."""
    console.print(f'[bold blue]Setting up symbolic storage for contract:[/bold blue] {options.contract_name}')

    # Get storage layout from forge inspect
    storage_data = run_forge_inspect(foundry, options.contract_name)

    # Generate storage constants
    storage_constants = generate_storage_constants(
        options.contract_name, options.solidity_version, storage_data['storage'], storage_data['types']
    )

    # Determine output file path
    if options.output_file:
        output_path = Path(options.output_file)
    else:
        output_path = foundry._root / 'test' / 'kontrol' / 'storage' / f'{options.contract_name}StorageConstants.sol'

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write storage constants file
    with open(output_path, 'w') as f:
        f.write(storage_constants)

    console.print(f'[bold green]Generated storage constants:[/bold green] {output_path}')

    # Generate KontrolTest contract if requested
    if options.test_contract:
        kontrol_test_content = generate_kontrol_test_contract(options.solidity_version)
        test_contract_path = foundry._root / 'test' / 'kontrol' / 'KontrolTest.sol'

        # Ensure test directory exists
        test_contract_path.parent.mkdir(parents=True, exist_ok=True)

        with open(test_contract_path, 'w') as f:
            f.write(kontrol_test_content)

        console.print(f'[bold green]Generated KontrolTest contract:[/bold green] {test_contract_path}')

        # Generate complete test contract with setUp function
        complete_test_content = generate_complete_test_contract(
            options.contract_name, options.solidity_version, storage_data['storage'], storage_data['types']
        )
        complete_test_path = foundry._root / 'test' / f'{options.contract_name}Test.sol'

        with open(complete_test_path, 'w') as f:
            f.write(complete_test_content)

        console.print(f'[bold green]Generated complete test contract:[/bold green] {complete_test_path}')

    console.print('[bold green]Symbolic storage setup completed successfully![/bold green]')
