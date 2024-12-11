// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test} from "forge-std/Test.sol";
import {KontrolCheats} from "kontrol-cheatcodes/KontrolCheats.sol";

contract BMCBoundTest is Test, KontrolCheats {
    uint x;

    function setUp() public {
        uint256 i = freshUInt256();
        for (uint j = 0; j < i; j++) {
            x += 1;
        }
    }

    function testBound() public view {
        assertLe(x, 3);
    }
}