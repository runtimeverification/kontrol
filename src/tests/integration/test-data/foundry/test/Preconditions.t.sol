// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.0;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract PreconditionsTest is Test, KontrolCheats {
    uint256 n;

    function setUp() public {
        kevm.symbolicStorage(address(this));
        vm.assume(n < 10);
    }

    function testAssume() public {
        assertLt(n, 10);
    }
}

