// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "src/cse/Branches.sol";

contract MergeKCFGTest is Test {

    function test_branch_merge(uint256 x, uint256 y, bool z) external view{
        vm.assume(x + y < 2 ** 64);
        try c.f(x, y, z) returns (uint256 res) {
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
