# Symbolic Storage Setup

Kontrol provides functionality to setup symbolic structured storage constants and test contracts for Solidity smart contracts. This feature helps developers create formal verification test contracts that can work with symbolic storage manipulation.

## Features

1. **Storage Constants Generation**: Automatically generates Solidity library with storage slot, offset, and size constants for all contract storage variables.
2. **KontrolTest Base Contract**: Generates a base test contract with utility functions for symbolic storage manipulation.
3. **Foundry Integration**: Uses `forge inspect` to automatically analyze contract storage layout.

## Usage

### Basic Usage

Setup symbolic storage constants for a contract:

```bash
kontrol setup-symbolic-storage ContractName
```

This will:
- Run `forge inspect ContractName storage --json` to get storage layout
- Generate `test/kontrol/storage/ContractNameStorageConstants.sol` with storage constants
- Use Solidity version 0.8.26 by default

### Advanced Usage

```bash
kontrol setup-symbolic-storage ContractName --solidity-version 0.8.24 --output-file custom/path/Storage.sol --test-contract
```

Options:
- `--solidity-version`: Specify Solidity version (default: 0.8.26)
- `--output-file`: Custom output file path
- `--test-contract`: Also generate KontrolTest base contract

### Generated Files

#### Storage Constants Library

The generated storage constants library contains constants for all storage variables:

```solidity
pragma solidity 0.8.26;

library ContractNameStorageConstants {
    uint256 public constant STORAGE_TOTALSUPPLY_SLOT = 0;
    uint256 public constant STORAGE_TOTALSUPPLY_OFFSET = 0;
    uint256 public constant STORAGE_TOTALSUPPLY_SIZE = 32;
    uint256 public constant STORAGE_BALANCES_SLOT = 1;
    uint256 public constant STORAGE_BALANCES_OFFSET = 0;
    uint256 public constant STORAGE_BALANCES_SIZE = 32;
    // ... more constants
}
```

#### KontrolTest Base Contract

The KontrolTest base contract provides utility functions for symbolic storage manipulation:

```solidity
pragma solidity 0.8.26;

import "forge-std/Vm.sol";
import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract KontrolTest is Test, KontrolCheats {
    // Utility functions for storage manipulation
    function _loadData(address, uint256, uint256, uint256) internal view returns (uint256);
    function _storeData(address, uint256, uint256, uint256, uint256) internal;
    function _loadMappingData(address, uint256, uint256, uint256, uint256, uint256) internal view returns (uint256);
    function _storeMappingData(address, uint256, uint256, uint256, uint256, uint256, uint256) internal;
    // ... more utility functions
}
```

## Example Usage in Test Contracts

Here's how to use the generated constants and base contract in your test:

```solidity
pragma solidity 0.8.26;

import "contracts/YourContract.sol";
import "test/kontrol/KontrolTest.sol";
import "test/kontrol/storage/YourContractStorageConstants.sol";

contract YourContractTest is KontrolTest {
    function testSymbolicStorage() external {
        YourContract contract = new YourContract();
        
        // Set up symbolic storage
        kevm.symbolicStorage(address(contract));
        
        // Use generated constants to manipulate storage
        uint256 symbolicValue = freshUInt256("test_value");
        vm.assume(symbolicValue > 0);
        
        _storeData(
            address(contract),
            YourContractStorageConstants.STORAGE_TOTALSUPPLY_SLOT,
            YourContractStorageConstants.STORAGE_TOTALSUPPLY_OFFSET,
            YourContractStorageConstants.STORAGE_TOTALSUPPLY_SIZE,
            symbolicValue
        );
        
        // Verify the storage was set correctly
        uint256 storedValue = _loadData(
            address(contract),
            YourContractStorageConstants.STORAGE_TOTALSUPPLY_SLOT,
            YourContractStorageConstants.STORAGE_TOTALSUPPLY_OFFSET,
            YourContractStorageConstants.STORAGE_TOTALSUPPLY_SIZE
        );
        
        assert(storedValue == symbolicValue);
    }
}
```

## Limitations

- Only works with Foundry projects andcontracts that can be analyzed by `forge inspect`
- Struct members are flattened into individual constants
- Array and mapping storage layouts follow Solidity conventions
