// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "forge-std/Test.sol";

contract TransientStorageTest is Test {
    function testTransientStoreLoad(uint256 key, uint256 value) public {
        // Store `value` at `key` in transient storage
        assembly {
            tstore(key, value)
        }

        uint256 loadedValue;

        // Load `value` from `key` in transient storage        
        assembly {
            loadedValue := tload(key)
        }

        assertEq(loadedValue, value, "TLOAD did not return the correct value");
    }
}