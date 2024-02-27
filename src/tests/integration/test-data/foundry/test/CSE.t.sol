// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

import "src/cse/Unary.sol";
import "src/cse/Binary.sol";
import "src/cse/SimpleWETH.sol";

contract CSETest is Test {
    Identity i;
    Multiply m;

    function setUp() external {
        i = new Identity();
        m = new Multiply();
    }

    // CSE challenge: External function call
    function test_identity(uint256 x, uint256 y) external view {
        vm.assume(x < 2 ** 64 && y < 2 ** 64);
        uint256 z = i.applyOp(x) + i.applyOp(y) + i.applyOp(y);
        assert(z == x + 2 * y);
    }
}
