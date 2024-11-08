// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";

contract RandomVarTest is Test {
    function test_randomBool() public {
        uint256 fresh_uint256 = vm.randomBool();
        assertGe(fresh_uint256, 0);
        assertLe(fresh_uint256, 1);
    }
}