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
        assert (a!=b);
    }
}
