// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";


contract Precondition {
    /// @custom:kontrol-precondition x >= 2,
    function totalSupply(uint256 x) public pure returns (uint256) { return x; }
}

contract PreconditionTest is  Test {
     /// @custom:kontrol-precondition x <= 7 * 2,
    function testPrecondition(uint256 x) public {
        Precondition p = new Precondition();
        uint256 r = p.totalSupply(x);
        assert(r <= 14);
    }
}