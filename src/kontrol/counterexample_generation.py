"""
Counterexample generation functionality for Kontrol.

This module provides functionality to generate Solidity test contracts with concrete
counterexample values extracted from failed proofs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
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
        raise ValueError("No failure info or models available for counterexample generation")

    if not proof.failure_info.failing_nodes:
        raise ValueError("No failing nodes available for counterexample generation")

    # Use the first failing node for counterexample generation
    failing_node_id = proof.failure_info.failing_nodes[0]

    if failing_node_id not in proof.failure_info.models:
        raise ValueError(f"No model available for failing node {failing_node_id}")

    model = proof.failure_info.models[failing_node_id]

    # Extract test information
    test_id = proof.id
    contract_name, method_name = test_id.split('.', 1)

    # Get the contract and method information
    contract, method = foundry.get_contract_and_method(test_id)

    # Convert model to concrete values
    concrete_values = _extract_concrete_values(model, method)

    # Generate the counterexample test contract
    test_contract = _generate_test_contract(
        contract_name=contract_name,
        method_name=method_name,
        concrete_values=concrete_values,
        method=method,
    )

    # Determine output path
    if output_dir is None:
        output_dir = foundry._root / 'test' / 'counterexamples'

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'{contract_name}Counterexample.sol'

    # Write the test contract
    with open(output_file, 'w') as f:
        f.write(test_contract)

    _LOGGER.info(f'Generated counterexample test: {output_file}')
    return output_file


def _extract_concrete_values(model: list[tuple[str, str]], method) -> dict[str, Any]:
    """Extract concrete values from the model for method parameters.

    Args:
        model: List of (variable, term) tuples from the model
        method: The contract method being tested

    Returns:
        Dictionary mapping parameter names to concrete values
    """
    concrete_values = {}

    # Parse model variables and extract values
    for var, term in model:
        # Look for symbolic variables that match method parameters
        if var.startswith('KV') and '_' in var:
            # Extract the parameter name from the symbolic variable
            # Format: KV0_paramName:Int -> paramName
            param_name = var.split('_', 1)[1].split(':')[0]

            # Convert the term to a concrete value
            concrete_value = _convert_term_to_value(term)
            if concrete_value is not None:
                concrete_values[param_name] = concrete_value

    return concrete_values


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

    _LOGGER.warning(f"Could not convert term to concrete value: {term}")
    return None


def _generate_test_contract(
    contract_name: str,
    method_name: str,
    concrete_values: dict[str, Any],
    method,
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
    test_contract = f'''// SPDX-License-Identifier: UNLICENSED
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
'''

    # Add comments showing the extracted values
    for param_name, value in concrete_values.items():
        test_contract += f'        // {param_name} = {value}\n'

    test_contract += f'''
        // Call the method with concrete values
        {contract_name.lower()}.{method_name}(
'''

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
    test_contract += '''
        // The proof failed, so this test should demonstrate the issue
        // Add specific assertions here based on what the proof was trying to verify
        console.log("Counterexample test executed with concrete values");
    }
}
'''

    return test_contract


def _format_value(value: Any, param_type: str) -> str:
    """Format a concrete value for use in Solidity code.

    Args:
        value: The concrete value
        param_type: The Solidity parameter type

    Returns:
        Formatted string for the value
    """
    if isinstance(value, bool):
        return 'true' if value else 'false'
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        if value.startswith('0x'):
            return value
        else:
            return f'"{value}"'
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
