"""
Counterexample generation functionality for Kontrol.

This module provides functionality to generate concrete test cases from Kontrol models
by concretizing symbolic storage values and creating failing test cases.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .foundry import Foundry
from .options import CounterexampleOptions
from .utils import console


def parse_kontrol_model_string(model_string: str) -> Dict[str, Any]:
    """Parse Kontrol model string output to extract variable assignments."""
    assignments = {}
    
    # Look for patterns like "var_name = value" or "var_name: value"
    patterns = [
        r'(\w+)\s*=\s*(\d+)',  # var = 123
        r'(\w+):\s*(\d+)',     # var: 123
        r'"(\w+)"\s*:\s*(\d+)', # "var": 123
        r'(\w+)\s*=\s*0x([0-9a-fA-F]+)',  # var = 0x123
        r'(\w+):\s*0x([0-9a-fA-F]+)',     # var: 0x123
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, model_string)
        for var_name, value in matches:
            try:
                if value.startswith('0x'):
                    assignments[var_name] = int(value, 16)
                else:
                    assignments[var_name] = int(value)
            except ValueError:
                assignments[var_name] = value
    
    return assignments


def extract_assignments_from_model_object(model_obj: Any) -> Dict[str, Any]:
    """Extract variable assignments from Kontrol's internal model object."""
    # This function will need to be updated once we know the actual structure
    # of Kontrol's model object. For now, return empty dict.
    assignments = {}
    
    # TODO: Implement based on actual Kontrol model object structure
    # The model object likely contains mappings from K variables to concrete values
    # We'll need to traverse it and extract the assignments
    
    return assignments


def extract_storage_assignments(assignments: Dict[str, Any]) -> Dict[str, Any]:
    """Extract storage-related assignments from model assignments."""
    storage_assignments = {}
    
    # Look for variables that match storage patterns
    storage_patterns = [
        r'STORAGE_\w+_SLOT',
        r'STORAGE_\w+_OFFSET', 
        r'STORAGE_\w+_SIZE',
        r'\w+_value',  # Variables ending with _value
        r'\w+_\w+_value',  # Struct member variables
    ]
    
    for var_name, value in assignments.items():
        for pattern in storage_patterns:
            if re.match(pattern, var_name):
                storage_assignments[var_name] = value
                break
    
    return storage_assignments


def generate_concrete_storage_setup(
    contract_name: str,
    storage_assignments: Dict[str, Any],
    storage_constants_path: Path,
    solidity_version: str
) -> str:
    """Generate concrete storage setup from model assignments."""
    lines = []
    lines.append(f'pragma solidity {solidity_version};')
    lines.append('')
    lines.append(f'import "contracts/{contract_name}.sol";')
    lines.append('import "test/kontrol/KontrolTest.sol";')
    lines.append(f'import "test/kontrol/storage/{contract_name}StorageConstants.sol";')
    lines.append('')
    lines.append(f'contract {contract_name}CounterexampleTest is KontrolTest {{')
    lines.append('')
    
    # Generate concrete setUp function
    lines.append(f'    function setUp{contract_name}Concrete({contract_name} _{contract_name.lower()}) internal {{')
    lines.append(f'        // Concrete storage setup based on counterexample model')
    lines.append('')
    
    # Group assignments by storage variable
    storage_vars = {}
    for var_name, value in storage_assignments.items():
        if var_name.endswith('_value'):
            base_name = var_name.replace('_value', '')
            if base_name not in storage_vars:
                storage_vars[base_name] = {}
            storage_vars[base_name]['value'] = value
        elif '_SLOT' in var_name:
            base_name = var_name.replace('_SLOT', '').replace('STORAGE_', '')
            if base_name not in storage_vars:
                storage_vars[base_name] = {}
            storage_vars[base_name]['slot'] = value
        elif '_OFFSET' in var_name:
            base_name = var_name.replace('_OFFSET', '').replace('STORAGE_', '')
            if base_name not in storage_vars:
                storage_vars[base_name] = {}
            storage_vars[base_name]['offset'] = value
        elif '_SIZE' in var_name:
            base_name = var_name.replace('_SIZE', '').replace('STORAGE_', '')
            if base_name not in storage_vars:
                storage_vars[base_name] = {}
            storage_vars[base_name]['size'] = value
    
    # Generate concrete storage assignments
    for var_name, var_data in storage_vars.items():
        if 'value' in var_data and 'slot' in var_data:
            lines.append(f'        // Set {var_name} to concrete value {var_data["value"]}')
            lines.append(f'        _storeData(')
            lines.append(f'            address(_{contract_name.lower()}),')
            lines.append(f'            {contract_name}StorageConstants.STORAGE_{var_name.upper()}_SLOT,')
            lines.append(f'            {contract_name}StorageConstants.STORAGE_{var_name.upper()}_OFFSET,')
            lines.append(f'            {contract_name}StorageConstants.STORAGE_{var_name.upper()}_SIZE,')
            lines.append(f'            {var_data["value"]}')
            lines.append(f'        );')
            lines.append('')
    
    lines.append('    }')
    lines.append('')
    
    # Generate counterexample test function
    lines.append(f'    function test{contract_name}Counterexample() external {{')
    lines.append(f'        {contract_name} contract = new {contract_name}();')
    lines.append(f'        setUp{contract_name}Concrete(contract);')
    lines.append('        ')
    lines.append('        // This test reproduces the counterexample found by Kontrol')
    lines.append('        // The storage is set to concrete values that lead to the violation')
    lines.append('        ')
    lines.append('        // Add your test logic here to reproduce the failure')
    lines.append('        // The contract should fail with the same error as in the symbolic execution')
    lines.append('    }')
    lines.append('}')
    
    return '\n'.join(lines)


def generate_mapping_concretization(
    contract_name: str,
    storage_assignments: Dict[str, Any],
    solidity_version: str
) -> str:
    """Generate mapping concretization code for specific key-value pairs."""
    lines = []
    lines.append('    // Mapping concretization based on counterexample')
    lines.append('    // Only concrete the mappings that appear in constraints')
    lines.append('')
    
    # Look for mapping-related assignments
    mapping_assignments = {}
    for var_name, value in storage_assignments.items():
        if 'mapping' in var_name.lower() or 'key' in var_name.lower():
            mapping_assignments[var_name] = value
    
    for var_name, value in mapping_assignments.items():
        lines.append(f'    // Concrete mapping {var_name} with key-value pair')
        lines.append(f'    // This would need to be customized based on the specific mapping structure')
        lines.append('')
    
    return '\n'.join(lines)


def foundry_counterexample_generation(foundry: Foundry, options: CounterexampleOptions) -> None:
    """Generate counterexample test from Kontrol model."""
    console.print(f'[bold blue]Generating counterexample for test:[/bold blue] {options.test_name}')
    
    # This function will be called from within Kontrol's proof execution
    # when a violation is found. The model data should be passed directly
    # rather than reading from files.
    
    console.print('[bold yellow]Counterexample generation requires integration with Kontrol proof execution.[/bold yellow]')
    console.print('[bold yellow]This function will be called automatically when violations are detected.[/bold yellow]')
    
    # TODO: Implement integration with Kontrol's proof execution
    # The model data should be available as an object and string from the proof result


def generate_counterexample_on_failure(
    proof,
    kcfg_explore,
    test_name: str,
    foundry: Foundry,
    solidity_version: str = '0.8.26'
) -> Optional[Path]:
    """Generate counterexample test when a proof failure is detected."""
    # This function should be called from the existing print_failure_info
    # or similar failure handling code in Kontrol
    
    try:
        # Extract model information from the proof failure
        # The exact method will depend on how Kontrol exposes the model data
        model_obj = getattr(proof, 'model', None)
        model_string = getattr(proof, 'model_string', None)
        
        if not model_obj and not model_string:
            console.print('[bold yellow]No model information available for counterexample generation[/bold yellow]')
            return None
        
        # Generate counterexample test
        return generate_counterexample_from_model(
            test_name=test_name,
            model_obj=model_obj,
            model_string=model_string,
            foundry=foundry,
            solidity_version=solidity_version
        )
        
    except Exception as e:
        console.print(f'[bold red]Error generating counterexample:[/bold red] {e}')
        return None


def generate_counterexample_from_model(
    test_name: str,
    model_obj: Any,
    model_string: str,
    foundry: Foundry,
    solidity_version: str = '0.8.26',
    output_file: Optional[str] = None
) -> Path:
    """Generate counterexample test from Kontrol model object and string."""
    console.print(f'[bold blue]Generating counterexample for test:[/bold blue] {test_name}')
    
    # Try to extract assignments from model object first
    assignments = extract_assignments_from_model_object(model_obj)
    
    # If no assignments from object, try parsing the string
    if not assignments:
        assignments = parse_kontrol_model_string(model_string)
    
    console.print(f'[bold green]Parsed {len(assignments)} variable assignments from model[/bold green]')
    
    # Extract storage assignments
    storage_assignments = extract_storage_assignments(assignments)
    console.print(f'[bold green]Found {len(storage_assignments)} storage-related assignments[/bold green]')
    
    if not storage_assignments:
        console.print('[bold yellow]No storage assignments found in model. Counterexample may not be meaningful.[/bold yellow]')
        return None
    
    # Find storage constants file
    contract_name = test_name.split('.')[0]
    storage_constants_path = foundry._root / 'test' / 'kontrol' / 'storage' / f'{contract_name}StorageConstants.sol'
    if not storage_constants_path.exists():
        console.print(f'[bold red]Storage constants file not found:[/bold red] {storage_constants_path}')
        console.print('Please run setup-symbolic-storage first to generate storage constants')
        return None
    
    # Generate counterexample test
    counterexample_content = generate_concrete_storage_setup(
        contract_name,
        storage_assignments,
        storage_constants_path,
        solidity_version
    )
    
    # Determine output file path
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = foundry._root / 'test' / f'{test_name}Counterexample.sol'
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write counterexample test
    with open(output_path, 'w') as f:
        f.write(counterexample_content)
    
    console.print(f'[bold green]Generated counterexample test:[/bold green] {output_path}')
    console.print('[bold green]Counterexample generation completed successfully![/bold green]')
    console.print('[bold yellow]Note: You may need to manually adjust the test logic to reproduce the specific failure.[/bold yellow]')
    
    return output_path
