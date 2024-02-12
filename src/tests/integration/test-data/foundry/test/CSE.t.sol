// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import "../src/CSE/Bounding.sol";
import "../src/CSE/ExternalFunctionCall.sol";
import "../src/CSE/Storage.sol";

contract CSETest is Test {
    Identity i;
    Multiply m;

    function setUp() external {
        i = new Identity();
        m = new Multiply();
    }

    function test_identity(uint256 x, uint256 y) external view {
        vm.assume(x < 2 ** 64 && y < 2 ** 64);
        uint256 z = i.applyOp(x) + i.applyOp(y) + i.applyOp(y);
        assert(z == x + 2 * y);
    }

    function test_multiply(uint x, uint y) external view {
      vm.assume(x < 2 ** 64 && y < 2 ** 64);
      uint256 z = m.applyOp(x, 10) + m.applyOp(y, 5);
      assert (z == 5 * ( 2 * x + y) );
    }
}
