// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

import "src/cse/Unary.sol";
import "src/cse/Binary.sol";
import "src/cse/WETH9.sol";

contract CSETest is Test {
    Identity i;
    AddConst c;
    Multiply m;

    function setUp() external {
        i = new Identity();
        c = new AddConst();
        m = new Multiply();
    }

    // CSE challenge: External function call
    function test_identity(uint256 x, uint256 y) external view {
        vm.assume(x < 2 ** 64 && y < 2 ** 64);
        uint256 z = i.applyOp(x) + i.applyOp(y) + i.applyOp(y);
        assert(z == x + 2 * y);
    }

    function test_add_const(uint256 x, uint256 y) external {
        vm.assume(x < 2 ** 64 && y < 2 ** 64);
        c.setConst(x);
        uint256 z = c.applyOp(y);
        assert(z == x + y);
    }
}
