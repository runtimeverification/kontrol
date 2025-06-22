// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "../src/ArithmeticContract.sol";

contract ArithmeticCallTest is Test {
    ArithmeticContract arith;

    function setUp() external {
        arith = new ArithmeticContract();
    }

    function test_double_add(uint x, uint y) external {
        uint z = arith.add(x, y);
        z = arith.add(z, y);
        assert(z > x);
    }

    function test_double_add_double_sub(uint x, uint y) external {
        uint a = arith.add(x, y);
        a = arith.add(a, y);
        uint b = arith.sub(x, y);
        b = arith.sub(b, y);
        assert (a != b);
    }

    function test_double_add_sub_external(uint x, uint y, uint z) external {
        uint a = arith.add_sub_external(x, y, z);
        a = arith.add_sub_external(a, y, z);
        assert(a > x);
    }

    function test_double_add_sub_external_revert(uint x, uint y, uint z) external {
        vm.assume(x == type(uint256).max);
        vm.assume(y > 0);

        // the call should revert due to overflow in `add`
        vm.expectRevert(); 
        uint a = arith.add_sub_external(x, y, z);
        assert(a > x);
    }

    function test_double_add_sub_external_prank(uint x, uint y, uint z) external {
        address prankCaller = address(0xBEEF);
    
        vm.prank(prankCaller);
        uint a = arith.add_sub_external(x, y, z);
        assert(a > x);
    }
}
