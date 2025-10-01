"""
Counterexample generation functionality for Kontrol.

This module provides functionality to generate Solidity test contracts with concrete
counterexample values extracted from failed proofs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from pathlib import Path

    from pyk.proof.reachability import APRProof

    from .foundry import Foundry

_LOGGER: Final = logging.getLogger(__name__)


def generate_counterexample_test(
    proof: APRProof,
    foundry: Foundry,
    output_dir: Path | None = None,
) -> Path:
    """Generate a Solidity test contract with concrete counterexample values.

    Args:
        proof: The failed proof containing model information
        foundry: The Foundry instance
        output_dir: Directory to write the counterexample test (default: test/counterexamples/)

    Returns:
        Path to the generated counterexample test file
    """
    if not proof.failure_info or not hasattr(proof.failure_info, 'models'):
        raise ValueError('No failure info or models available for counterexample generation')

    if not hasattr(proof.failure_info, 'failing_nodes') or not proof.failure_info.failing_nodes:
        raise ValueError('No failing nodes available for counterexample generation')

    # Use the first failing node for counterexample generation
    failing_node_id = next(iter(proof.failure_info.failing_nodes))  # type: ignore

    if failing_node_id not in proof.failure_info.models:
        raise ValueError(f'No model available for failing node {failing_node_id}')

    model = proof.failure_info.models[failing_node_id]

    # Extract test information
    test_id = proof.id
    # Replace % with / to get proper path
    test_path = test_id.replace('%', '/')

    # Extract contract name and method from path like 'test/SimpleStorageTest.test_storage_setup(...):0'
    if '/' in test_path:
        path_parts = test_path.split('/')
        contract_and_method = path_parts[-1]  # Get 'SimpleStorageTest.test_storage_setup(...):0'
    else:
        contract_and_method = test_path

    contract_name, method_name = contract_and_method.split('.', 1)

    # Remove version number from method_name if present (e.g., 'test_storage_setup(...):0' -> 'test_storage_setup(...)')
    if ':' in method_name:
        method_name = method_name.rsplit(':', 1)[0]

    # Extract just the function name without parameter types (e.g., 'test_storage_setup(...)' -> 'test_storage_setup')
    if '(' in method_name:
        method_name = method_name.split('(')[0]

    # Create clean test_id without version for method lookup
    clean_test_id = f'{contract_name}.{method_name}'

    # For test contracts, use the full path with % instead of /
    test_contract_id = f'test%{contract_name}.{method_name}'

    # Get the contract and method information
    try:
        contract, method = foundry.get_contract_and_method(clean_test_id)
    except KeyError:
        try:
            contract, method = foundry.get_contract_and_method(test_contract_id)
        except KeyError:
            # If it's a test contract, we'll extract the method info from the test file
            method = None
            contract = None

    # Convert model to concrete values
    concrete_values = _extract_concrete_values(model, method)

    # Find and copy the original test file
    original_test_file = _find_original_test_file(foundry, test_id)

    # If we have the contract, try to get the file path from it
    if contract and hasattr(contract, 'contract_name_with_path'):
        contract_path = contract.contract_name_with_path
        # Convert % to / and try to find the file
        file_path = contract_path.replace('%', '/') + '.sol'
        potential_file = foundry._root / file_path
        if potential_file.exists():
            original_test_file = potential_file
        else:
            # Try with .t.sol extension
            file_path_t = contract_path.replace('%', '/') + '.t.sol'
            potential_file_t = foundry._root / file_path_t
            if potential_file_t.exists():
                original_test_file = potential_file_t

    if original_test_file and original_test_file.exists():
        # Copy the original test file and insert concrete assignments
        test_contract = _copy_and_modify_test_file(original_test_file, method_name, concrete_values, method)
    else:
        # Fallback to generating a new test contract
        test_contract = _generate_counterexample_test_contract(
            contract_name=contract_name,
            method_name=method_name,
            concrete_values=concrete_values,
            method=method,
        )

    if output_dir is None:
        # Placing the counterexample test file in the same directory as the original test file
        if original_test_file and original_test_file.exists():
            output_dir = original_test_file.parent
        else:
            output_dir = foundry._root / 'test'

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'{contract_name}CounterexampleTest.t.sol'

    # Write the test contract
    with open(output_file, 'w') as f:
        f.write(test_contract)

    _LOGGER.info(f'Generated counterexample test: {output_file}')
    return output_file


def _extract_concrete_values(model: list[tuple[str, str]], method: Any) -> dict[str, Any]:
    """Extract concrete values from the model for method parameters.

    Args:
        model: List of (variable, term) tuples from the model
        method: The contract method being tested (can be None for test contracts)

    Returns:
        Dictionary mapping parameter names to concrete values
    """
    concrete_values = {}

    if method is None:
        # For test contracts, extract parameter names directly from model variables
        for var, term in model:
            # Look for symbolic variables that match the pattern KV{idx}_{paramName}
            if var.startswith('KV') and '_' in var:
                # Extract the parameter name from the symbolic variable
                # Format: KV0_totalSupply:Int -> totalSupply
                param_name = var.split('_', 1)[1].split(':')[0]

                # Convert the term to a concrete value
                concrete_value = _convert_term_to_value(term)
                if concrete_value is not None:
                    concrete_values[param_name] = concrete_value
        return concrete_values

    # Create a mapping from symbolic variable names to original parameter names
    var_to_param = {}

    try:
        for input_param in method.inputs:
            # The symbolic variable name is stored in input_param.arg_name
            # Format: KV0_totalSupply -> _totalSupply (for _totalSupply)
            # Format: KV0_someParam -> someParam (for someParam)
            var_to_param[input_param.arg_name] = input_param.name
    except Exception:
        # Fallback: try to access as attributes
        if hasattr(method, 'inputs') and hasattr(method.inputs, '__iter__'):
            for input_param in list(method.inputs):
                try:
                    var_to_param[input_param.arg_name] = input_param.name
                except Exception:
                    continue

    # Parse model variables and extract values
    for var, term in model:
        # Look for symbolic variables that match method parameters
        if var in var_to_param:
            # Use the original parameter name (preserving underscores)
            param_name = var_to_param[var]

            # Convert the term to a concrete value
            concrete_value = _convert_term_to_value(term)
            if concrete_value is not None:
                concrete_values[param_name] = concrete_value

    return concrete_values


def _find_original_test_file(foundry: Foundry, test_id: str) -> Path | None:
    """Find the original test file for a given test ID.

    Args:
        foundry: The Foundry instance
        test_id: The test ID (e.g., "test%SimpleStorageTest.test_storage_setup(...):0")

    Returns:
        Path to the original test file, or None if not found
    """
    # Replace % with / to get proper path
    test_path = test_id.replace('%', '/')

    # Extract contract name and method from path
    if '/' in test_path:
        path_parts = test_path.split('/')
        contract_and_method = path_parts[-1]  # Get "SimpleStorageTest.test_storage_setup(...):0"
    else:
        contract_and_method = test_path

    contract_name, method_name = contract_and_method.split('.', 1)

    # Remove version number from method_name if present
    if ':' in method_name:
        method_name = method_name.rsplit(':', 1)[0]

    # Extract just the function name without parameter types (e.g., "test_storage_setup(...)" -> "test_storage_setup")
    if '(' in method_name:
        method_name = method_name.split('(')[0]

    # Look for test files in the test directory
    test_dir = foundry._root / 'test'
    if not test_dir.exists():
        return None

    # Search for files that might contain the test
    test_files = list(test_dir.glob('*.sol'))

    for test_file in test_files:
        try:
            with open(test_file, 'r') as f:
                content = f.read()
                # Check if this file contains the test method and contract
                has_method = f'function {method_name}(' in content
                has_contract = contract_name in content
                if has_method and has_contract:
                    return test_file
        except Exception:
            continue

    return None


def _copy_and_modify_test_file(
    original_file: Path, method_name: str, concrete_values: dict[str, Any], method: Any
) -> str:
    """Copy the original test file and insert concrete assignments into the failing method.

    Args:
        original_file: Path to the original test file
        method_name: Name of the failing test method
        concrete_values: Dictionary of parameter names to concrete values (keyed by symbolic var name suffix)
        method: The contract method object

    Returns:
        Modified test file content
    """
    with open(original_file, 'r') as f:
        content = f.read()

    # Extract the actual parameter names from the function signature in the file
    import re

    function_sig_pattern = r'function\s+' + re.escape(method_name) + r'\s*\(([^)]*)\)'
    match = re.search(function_sig_pattern, content)

    actual_param_names = []
    param_types = {}
    if match:
        params_str = match.group(1)
        # Parse each parameter: "uint256 totalSupply, address _owner, ..."
        for param in params_str.split(','):
            param = param.strip()
            if param:
                parts = param.split()
                if len(parts) >= 2:
                    param_type = parts[0]
                    param_name = parts[1]
                    actual_param_names.append(param_name)
                    param_types[param_name] = param_type

    # Map concrete values to actual parameter names
    # The concrete_values dict is keyed by the suffix after KV{idx}_
    # We need to match these to the actual parameter names
    assignments = []

    for param_name in actual_param_names:
        # Try to find this parameter in concrete_values
        # It might be stored without the leading underscore
        value = None
        param_type = param_types.get(param_name, 'uint256')

        # Try exact match first
        if param_name in concrete_values:
            value = concrete_values[param_name]
        # Try without leading underscore
        elif param_name.startswith('_') and param_name[1:] in concrete_values:
            value = concrete_values[param_name[1:]]
        # Try with leading underscore added
        elif f'_{param_name}' in concrete_values:
            value = concrete_values[f'_{param_name}']

        if value is not None:
            assignments.append(f'        {param_name} = {_format_value(value, param_type)};')

    # Find the test method and insert assignments
    import re

    # Pattern to match the function signature
    function_pattern = r'(function\s+' + re.escape(method_name) + r'\s*\([^{]*\)\s*public[^{]*\{)'

    def insert_assignments(match: Any) -> str:
        function_start = match.group(1)
        return (
            f'{function_start}\n        // Counterexample values from failed proof:\n' + '\n'.join(assignments) + '\n'
        )

    # Replace the function with assignments inserted
    modified_content = re.sub(function_pattern, insert_assignments, content)

    # If no match found, try a more flexible pattern
    if modified_content == content:
        # Look for the function and insert after the opening brace
        lines = content.split('\n')
        modified_lines = []
        in_target_function = False
        brace_count = 0

        for line in lines:
            modified_lines.append(line)

            # Check if we're entering the target function
            if f'function {method_name}(' in line and 'public' in line:
                in_target_function = True
                brace_count = 0

            if in_target_function:
                # Count braces to find the opening brace
                brace_count += line.count('{') - line.count('}')

                # If we just entered the function body (opening brace)
                if brace_count == 1 and '{' in line:
                    # Insert assignments after the opening brace
                    modified_lines.append('        // Counterexample values from failed proof:')
                    for assignment in assignments:
                        modified_lines.append(assignment)
                    in_target_function = False

        modified_content = '\n'.join(modified_lines)

    return modified_content


def _convert_term_to_value(term: str) -> Any:
    """Convert a K term to a concrete Solidity value.

    Args:
        term: The K term (e.g., "123", "0x1234", "true")

    Returns:
        The concrete value or None if conversion fails
    """
    # Remove K-specific syntax
    term = term.strip()

    # Handle integers
    if term.isdigit():
        return int(term)

    # Handle hex values
    if term.startswith('0x'):
        return term

    # Handle boolean values
    if term.lower() in ('true', 'false'):
        return term.lower() == 'true'

    # Handle quoted strings
    if term.startswith('"') and term.endswith('"'):
        return term[1:-1]

    # Handle K-specific integer tokens
    if term.endswith(':Int'):
        try:
            return int(term[:-4])
        except ValueError:
            pass

    # Handle K-specific boolean tokens
    if term.endswith(':Bool'):
        return term[:-5].lower() == 'true'

    # Handle K-specific address tokens
    if term.endswith(':Addr'):
        addr = term[:-5]
        if addr.startswith('0x'):
            return addr
        else:
            # Convert to hex if it's a decimal
            try:
                return hex(int(addr))
            except ValueError:
                pass

    _LOGGER.warning(f'Could not convert term to concrete value: {term!r}')
    return None


def _generate_counterexample_test_contract(
    contract_name: str,
    method_name: str,
    concrete_values: dict[str, Any],
    method: Any,
) -> str:
    """Generate a Solidity test contract with concrete counterexample values.

    Args:
        contract_name: Name of the contract being tested
        method_name: Name of the method being tested
        concrete_values: Dictionary of parameter names to concrete values
        method: The contract method object

    Returns:
        The generated Solidity test contract code
    """
    # Generate concrete assignments for the test function
    assignments = []
    for param_name, value in concrete_values.items():
        # Try to determine the correct type for formatting
        param_type = 'uint256'  # Default fallback
        if method and hasattr(method, 'inputs'):
            for input_param in method.inputs:
                if input_param.name == param_name:
                    param_type = input_param.type
                    break
        assignments.append(f'        {param_name} = {_format_value(value, param_type)};')

    # Generate parameter list for the test function
    param_list = []
    if method and hasattr(method, 'inputs'):
        for param in method.inputs:
            param_name = param.name
            param_type = param.type
            param_list.append(f'{param_type} {param_name}')
    else:
        # If no method info, generate parameters from concrete values
        for param_name in concrete_values.keys():
            param_list.append(f'uint256 {param_name}')

    # Generate the test contract
    test_contract = f"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {{Test, console}} from "forge-std/Test.sol";
import {{{contract_name}}} from "../src/{contract_name}.sol";

contract {contract_name}TestCounterexample is Test {{
    {contract_name} public {contract_name.lower()};

    function setUp() public {{
        {contract_name.lower()} = new {contract_name}();
    }}

    function {method_name}({', '.join(param_list)}) public {{
        // Counterexample values from failed proof:
{chr(10).join(assignments)}

        // Original test logic would go here
        // This test reproduces the counterexample that caused the proof to fail
        console.log("Counterexample test executed with concrete values");
    }}
}}
"""

    return test_contract


def _generate_test_contract(
    contract_name: str,
    method_name: str,
    concrete_values: dict[str, Any],
    method: Any,
) -> str:
    """Generate a Solidity test contract with concrete counterexample values.

    Args:
        contract_name: Name of the contract being tested
        method_name: Name of the method being tested
        concrete_values: Dictionary of parameter names to concrete values
        method: The contract method object

    Returns:
        The generated Solidity test contract code
    """
    # Generate parameter list for the test function
    param_list = []
    for param in method.parameters:
        param_name = param['name']
        param_type = param['type']

        if param_name in concrete_values:
            value = concrete_values[param_name]
            param_list.append(f'{param_type} {param_name} = {_format_value(value, param_type)}')
        else:
            # Use a default value if no concrete value available
            param_list.append(f'{param_type} {param_name} = {_get_default_value(param_type)}')

    # Generate the test contract
    test_contract = f"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "forge-std/console.sol";
import "src/{contract_name}.sol";

/**
 * @title {contract_name}Counterexample
 * @dev Counterexample test generated from failed proof
 * @notice This test reproduces the counterexample that caused the proof to fail
 */
contract {contract_name}Counterexample is Test {{
    {contract_name} public {contract_name.lower()};

    function setUp() public {{
        {contract_name.lower()} = new {contract_name}();
    }}

    /**
     * @dev Test that reproduces the counterexample
     * This test uses concrete values extracted from the failed proof model
     */
    function testCounterexample() public {{
        // Counterexample values from failed proof:
"""

    # Add comments showing the extracted values
    for param_name, value in concrete_values.items():
        test_contract += f'        // {param_name} = {value}\n'

    test_contract += f"""
        // Call the method with concrete values
        {contract_name.lower()}.{method_name}(
"""

    # Add the method call with concrete values
    param_values = []
    for param in method.parameters:
        param_name = param['name']
        if param_name in concrete_values:
            param_values.append(param_name)
        else:
            param_values.append(_get_default_value(param['type']))

    test_contract += '            ' + ',\n            '.join(param_values) + '\n        );\n'

    # Add assertions to verify the counterexample
    test_contract += """
        // The proof failed, so this test should demonstrate the issue
        // Add specific assertions here based on what the proof was trying to verify
        console.log("Counterexample test executed with concrete values");
    }
}
"""

    return test_contract


def _format_value(value: Any, param_type: str) -> str:
    """Format a concrete value for use in Solidity code.

    Args:
        value: The concrete value
        param_type: The Solidity parameter type

    Returns:
        Formatted string for the value
    """
    # Handle bool type specifically - convert 0/1 to false/true
    if param_type == 'bool':
        if isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, int):
            return 'true' if value != 0 else 'false'
        else:
            return 'false'
    # Handle address type - wrap in address()
    elif param_type == 'address':
        if isinstance(value, str) and value.startswith('0x'):
            return f'address({value})'
        elif isinstance(value, int):
            if value == 0:
                return 'address(0)'
            else:
                return f'address({hex(value)})'
        else:
            return 'address(0)'
    elif isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        if value.startswith('0x'):
            return value
        else:
            return f'{value!r}'
    else:
        return str(value)


def _get_default_value(param_type: str) -> str:
    """Get a default value for a Solidity parameter type.

    Args:
        param_type: The Solidity parameter type

    Returns:
        Default value string
    """
    if param_type.startswith('uint') or param_type.startswith('int'):
        return '0'
    elif param_type == 'bool':
        return 'false'
    elif param_type == 'address':
        return 'address(0)'
    elif param_type == 'string':
        return '""'
    elif param_type == 'bytes':
        return '""'
    else:
        return '0'
