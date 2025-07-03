// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract SymbolicStore {
    uint256 private testNumber = 1337; // slot 0
    constructor() {}
}

contract SymbolicStorageTest is Test, KontrolCheats { 

    function testEmptyInitialStorage(uint256 slot) public {
        bytes32 storage_value = vm.load(address(vm), bytes32(slot));
        assertEq(uint256(storage_value), 0);
    }
}
