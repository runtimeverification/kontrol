// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

contract Dummy {}

contract ComputeCreateAddressTest is Test {
    function test_computeCreateAddress() public {
        uint64 nonce = vm.getNonce(address(this));
        address predicted = vm.computeCreateAddress(address(this), nonce);
        Dummy d = new Dummy();
        assertEq(address(d), predicted);
    }
}