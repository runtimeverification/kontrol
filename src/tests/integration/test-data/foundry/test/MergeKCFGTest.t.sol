// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "src/Branches.sol";

contract MergeKCFGTest is Test {
    Branches c;

    function setUp() external {
        c = new Branches();
    }

    function test_branch_merge(uint256 x, uint256 y, bool z) external{
        vm.assume(x <= type(uint256).max - y);
        try c.applyOp(x, y, z) returns (uint256 res) {
            // This check will fail if the backend cannot recover the preds in the merged postcondition
            // If so, assert res == x + y | res == x * y will pass
            // If so, we should not always use merge_node, but provide both on need.
            if (z) {
                assert(res == x + y);
            } else {
                assert(res == x * y);
            }
        } catch {
            assert(x != 0 && 2 ** 62 / x < y && !z);
        }
    }
}