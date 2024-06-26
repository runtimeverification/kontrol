// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract InitCodeBranchTest is Test, KontrolCheats {

    uint a;
    uint b;

    constructor() public payable {
        kevm.symbolicStorage(address(this));
        if(a <= 10) {
            b = 1;
        }
        else {
            b = 2;
        }
    }

    function test_branch() public {
        assertEq(b, 1);
    }
}
