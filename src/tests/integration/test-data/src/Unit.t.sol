// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";

contract UnitTest is Test {
    function test_assertEq() public pure {
        assertEq(uint256(11), 11);
    }

    function test_assertEq(address a, address b) public pure {
        vm.assume(a == b);
        assertEq(a, b);
    }

    function test_assertEq(bool a, bool b) public pure {
        vm.assume(a == b);
        assertEq(a, b);
    }

    function test_assertEq(bytes32 a, bytes32 b) public pure {
        vm.assume(a == b);
        assertEq(a, b);
    }

    function test_assertEq(int256 a, int256 b) public pure {
        vm.assume(a == b);
        assertEq(a, b);
    }

    function test_assertEq_err() public {
        string memory expected = "throw test: 11 != 121";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertEq(uint256(11), 121, err);
    }

    function test_assertEq_address_err() public {
        string memory expected = "throw test: 0x0000000000000000000000000000000000000000 != 0x0000000000000000000000000000000000000001";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertEq(address(0), address(1), err);
    }

    function test_assertEq_bool_err() public {
        string memory expected = "throw test: true != false";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertEq(true, false, err);
    }

    function test_assertEq_bytes32_err() public {
        string memory expected = "throw test: 0x0000000000000000000000000000000000000000000000000000000000000000 != 0x7465737400000000000000000000000000000000000000000000000000000000";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertEq(bytes32(0), bytes32("test"), err);
    }

    function test_assertEq_int256_err() public {
        string memory expected = "throw test: 1 != 0";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertEq(int256(1), int256(0), err);
    }

    function test_assertEq_error_string() public {
        vm.expectRevert("assertion failed: 100 != 50");
        assertEq(uint256(100), 50);
    }

    function test_assertNotEq() public pure {
        assertNotEq(uint256(11), 100);
    }

    function test_assertNotEq(address a, address b) public pure {
        vm.assume(a != b);
        assertNotEq(a, b);
    }

    function test_assertNotEq(bool a, bool b) public pure {
        vm.assume(a != b);
        assertNotEq(a, b);
    }

    function test_assertNotEq(bytes32 a, bytes32 b) public pure {
        vm.assume(a != b);
        assertNotEq(a, b);
    }

    function test_assertNotEq(int256 a, int256 b) public pure {
        vm.assume(a != b);
        assertNotEq(a, b);
    }

    function test_assertNotEq_err() public {
        string memory expected = "throw test: 121 == 121";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertNotEq(uint256(121), 121, err);
    }

    function test_assertNotEq_address_err() public {
        string memory expected = "throw test: 0x0000000000000000000000000000000000000001 == 0x0000000000000000000000000000000000000001";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertNotEq(address(1), address(1), err);
    }

    function test_assertNotEq_bool_err() public {
        string memory expected = "throw test: false == false";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertNotEq(false, false, err);
    }

    function test_assertNotEq_bytes32_err() public {
        string memory expected = "throw test: 0x0000000000000000000000000000000000000000000000000000000000000000 == 0x0000000000000000000000000000000000000000000000000000000000000000";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertNotEq(bytes32(0), bytes32(0), err);
    }

    function test_assertNotEq_int256_err() public {
        string memory expected = "throw test: 0 == 0";
        string memory err = "throw test";
        vm.expectRevert(bytes(expected));
        assertNotEq(int256(0), int256(0), err);
    }

    function test_assertTrue(bool value) public pure {
        vm.assume(value == true);
        assertTrue(value);
    }

    function test_assertTrue_err() public {
        string memory err = "throw test";
        vm.expectRevert(bytes(err));
        assertTrue(false, err);
    }

    function test_assertFalse(bool value) public pure {
        vm.assume(value == false);
        assertFalse(value);
    }

    function test_assertFalse_err() public {
        string memory err = "throw test";
        vm.expectRevert(bytes(err));
        assertFalse(true, err);
    }

    function test_assertGt_assertGe(int256 a, int256 b) public pure {
        vm.assume(a > b);
        assertGt(a, b);
        assertGe(a, b);
    }

    function test_assertGt_assertGe(uint256 a, uint256 b) public pure {
        vm.assume(a > b);
        assertGt(a, b);
        assertGe(a, b);
    }

    function test_assertLt_assertLe(int256 a, int256 b) public pure {
        vm.assume(a < b);
        assertLt(a, b);
        assertLe(a, b);
    }

    function test_assertLt_assertLe(uint256 a, uint256 b) public pure {
        vm.assume(a < b);
        assertLt(a, b);
        assertLe(a, b);
    }
    function test_assertLt_assertLe_int_concrete() public pure {
        int256 a = -11;
        int256 b = 1;
        assertLt(a, b);
        assertLe(a, b);
    }
}
