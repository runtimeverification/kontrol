// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract AssertNestedTest is Test, KontrolCheats {
    function test_assert_true_nested() public pure {
        assert(true);
    }
}
