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

    function test_assertApproxEqAbs_uint(uint256 a, uint256 b, uint256 maxDelta) public pure {
        vm.assume(maxDelta >= max(a, b) - min(a, b));
        assertApproxEqAbs(a, b, maxDelta);
    }

    function test_assertApproxEqAbs_uint_err() public {
        string memory err = "throw test";
        string memory err_lt = "throw test: 11 !~= 121 (max delta: 100, real delta: 110)";
        vm.expectRevert(bytes(err_lt));
        assertApproxEqAbs(uint256(11), uint(121), 100, err);
    }

    function test_assertApproxEqAbs_int_same_sign(uint256 a, uint256 b, uint256 maxDelta) public pure {
        vm.assume(a > 0);
        vm.assume(b > 0);
        vm.assume(a <= uint256(type(int256).max));
        vm.assume(b <= uint256(type(int256).max));
        vm.assume(maxDelta >= max(a, b) - min(a, b));
        int256 pos_a = int256(a);
        int256 pos_b = int256(b); 
        int256 neg_a = -pos_a;
        int256 neg_b = -pos_b;              
        assertApproxEqAbs(pos_a, pos_b, maxDelta);
        assertApproxEqAbs(neg_a, neg_b, maxDelta);
    }

    function test_assertApproxEqAbs_int_same_sign_err() public {
        int256 neg_a = -2;
        int256 neg_b = -22;
        uint256 maxDelta = 10;
        string memory err = "throw test";
        string memory err_neg = "throw test: -2 !~= -22 (max delta: 10, real delta: 20)";
        vm.expectRevert(bytes(err_neg));
        assertApproxEqAbs(neg_a, neg_b, maxDelta, err);
    }

    function test_assertApproxEqAbs_int_opp_sign(uint256 a, uint256 b, uint256 maxDelta) public pure {
        vm.assume(a > 0);
        vm.assume(b > 0);
        vm.assume(a <= uint256(type(int256).max));
        vm.assume(b <= uint256(type(int256).max));
        vm.assume(maxDelta >= a + b);
        int256 pos_a = int256(a);
        int256 pos_b = int256(b); 
        int256 neg_a = -pos_a;
        int256 neg_b = -pos_b;              
        assertApproxEqAbs(pos_a, neg_b, maxDelta);
        assertApproxEqAbs(neg_a, pos_b, maxDelta);
    }

    function test_assertApproxEqAbs_int_opp_sign_err() public {
        int256 pos_a = 2;
        int256 neg_b = -18; 
        uint256 maxDelta = 10;
        string memory err = "throw test";
        string memory err_pos_a_neg_b = "throw test: 2 !~= -18 (max delta: 10, real delta: 20)";
        vm.expectRevert(bytes(err_pos_a_neg_b));
        assertApproxEqAbs(pos_a, neg_b, maxDelta, err);
    }

    function test_assertApproxEqAbs_int_zero_cases(uint256 a, uint256 maxDelta) public pure {
        vm.assume(a > 0);
        vm.assume(a <= uint256(type(int256).max));
        vm.assume(maxDelta >= a);
        int256 pos_a = int256(a);
        int256 neg_a = -pos_a;
        int256 int_zero = int256(0);
        assertApproxEqAbs(int_zero, int_zero, 0);
        assertApproxEqAbs(int_zero, int_zero, maxDelta);
        assertApproxEqAbs(pos_a, int_zero, maxDelta);
        assertApproxEqAbs(int_zero, pos_a, maxDelta);
        assertApproxEqAbs(neg_a, int_zero, maxDelta);
        assertApproxEqAbs(int_zero, neg_a, maxDelta);
    }

    function test_assertApproxEqAbs_int_zero_cases_err() public {
        int256 neg_a = -2;
        int256 int_zero = int256(0);
        uint256 maxDelta = 1;
        string memory err = "throw test";
        string memory err_zero_neg_a = "throw test: 0 !~= -2 (max delta: 1, real delta: 2)";
        vm.expectRevert(bytes(err_zero_neg_a));
        assertApproxEqAbs(int_zero, neg_a, maxDelta, err);
    }

    function test_assertApproxEqRel_uint_unit() public pure {
        uint256 zero = 0;
        uint256 a = 8;
        uint256 b = 10;
        uint256 percentDelta = 1e18;
        assertApproxEqRel(zero, zero, percentDelta);
        assertApproxEqRel(zero, b, percentDelta);
        assertApproxEqRel(a, b, percentDelta);
    }

    function test_assertApproxEqRel_uint_err() public {
        uint256 a = 4;
        uint256 b = 2;
        uint256 percentDelta = 5e17;
        string memory err = "throw test";
        string memory err_a_b = "throw test: 4 !~= 2 (max delta: 50.0000000000000000%, real delta: 100.0000000000000000%)";
        vm.expectRevert(bytes(err_a_b));
        assertApproxEqRel(a, b, percentDelta, err);
    }

    function test_assertApproxEqRel_int_same_sign_unit() public pure {
        int256 pos_a = 8;
        int256 pos_b = 10;
        int256 neg_a = -8;
        int256 neg_b = -10;
        uint256 percentDelta = 1e18;
        assertApproxEqRel(pos_a, pos_b, percentDelta);
        assertApproxEqRel(neg_a, neg_b, percentDelta);
    }

    function test_assertApproxEqRel_int_same_sign_err() public {
        int256 neg_a = -4;
        int256 neg_b = -2;
        uint256 percentDelta = 5e17;
        string memory err = "throw test";
        string memory err_neg_a_neg_b = "throw test: -4 !~= -2 (max delta: 50.0000000000000000%, real delta: 100.0000000000000000%)";
        vm.expectRevert(bytes(err_neg_a_neg_b));
        assertApproxEqRel(neg_a, neg_b, percentDelta, err);
    }

    function test_assertApproxEqRel_int_opp_sign_unit() public pure {
        int256 pos_a = 2;
        int256 pos_b = 3;
        int256 neg_a = -2;
        int256 neg_b = -3;
        uint256 percentDelta = 2e18;
        assertApproxEqRel(pos_a, neg_b, percentDelta);
        assertApproxEqRel(neg_a, pos_b, percentDelta);
    }

    function test_assertApproxEqRel_int_opp_sign_err() public {
        int256 pos_a = 4;
        int256 neg_b = -2;
        uint256 percentDelta = 1e18;
        string memory err = "throw test";
        string memory err_pos_a_neg_b = "throw test: 4 !~= -2 (max delta: 100.0000000000000000%, real delta: 300.0000000000000000%)";
        vm.expectRevert(bytes(err_pos_a_neg_b));
        assertApproxEqRel(pos_a, neg_b, percentDelta, err);
    }

    function test_assertApproxEqRel_int_zero_cases_unit() public pure {
        int256 zero = 0;
        int256 pos_b = 3;
        int256 neg_b = -3;
        uint256 percentDelta = 1e18;
        assertApproxEqRel(zero, zero, percentDelta);
        assertApproxEqRel(zero, pos_b, percentDelta);
        assertApproxEqRel(zero, neg_b, percentDelta);
    }

    function test_assertApproxEqRel_int_zero_cases_err() public {
        int256 zero = 0;
        int256 neg_b = -2;
        uint256 percentDelta = 5e17;
        string memory err = "throw test";
        string memory err_zero_neg_b = "throw test: 0 !~= -2 (max delta: 50.0000000000000000%, real delta: 100.0000000000000000%)";
        vm.expectRevert(bytes(err_zero_neg_b));
        assertApproxEqRel(zero, neg_b, percentDelta, err);
    }

    /****************************
    * Internal helper functions *
    *****************************/

    function max(uint256 a, uint256 b) internal pure returns (uint256) {
        return a > b ? a : b;
    }

    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a > b ? b : a;
    }
}
