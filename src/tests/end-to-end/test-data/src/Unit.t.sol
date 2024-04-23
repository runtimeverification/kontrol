// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";

contract UnitTest is Test {
    function test_assertEq_0() public pure {
        assertEq(uint256(11), 11);
    }

    function test_assertEq_1(address a, address b) public pure {
        vm.assume(a == b);
        assertEq(a, b);
    }

    function test_assertEq_2(bool a, bool b) public pure {
        vm.assume(a == b);
        assertEq(a, b);
    }

    function test_assertEq_3(bytes32 a, bytes32 b) public pure {
        vm.assume(a == b);
        assertEq(a, b);
    }

    function test_assertTrue(bool value) public pure {
        vm.assume(value == true);
        assertTrue(value);
    }

    function test_assertNotEq(address a, address b) public pure {
        vm.assume(a != b);
        assertNotEq(a, b);
    }

    function test_assertGt_assertGe(uint256 a, uint256 b) public pure {
        vm.assume(a > b);
        assertGt(a, b);
        assertGe(a, b);
    }

    function test_assertLt_assertLe(uint256 a, uint256 b) public pure {
        vm.assume(a < b);
        assertLt(a, b);
        assertLe(a, b);
    }
}
