// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract MergeTest is Test, KontrolCheats {
    uint y;

    function test_branch_merge(uint x) public {
        if (x < 10) {
            y = 0;
        } else {
            y = 1;
        }
        assert(y < 2);
    }
}
