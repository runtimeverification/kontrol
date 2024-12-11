// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";

library LibrarySum {
    function sum(uint256 a, uint256 b) external pure returns (uint256 res) {
        res = a + b;
    }
}

library LibraryEq {
    function eq(uint256 a, uint256 b, uint256 c) internal pure returns (bool res) {
       uint256 sum = LibrarySum.sum(a, b);
       return (sum == c);
    }
}

contract ExternalNestedLibraryTest is Test {
    uint256 public z = 10;

    function testExtLibs() public view {
        uint256 x = 3;
        uint256 y = 7;
        bool res = LibraryEq.eq(x, y, z);
        assert(res);
    }
}
