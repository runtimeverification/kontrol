// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import {Test, console} from "forge-std/Test.sol";

contract TestNumber is Test{
    uint256 public testNumber ;

    constructor(uint256 initial){
        testNumber = initial;
    }

    function t(uint256 a) public returns (uint256) {
        uint256 b = 0;
        testNumber = a;
        emit log_string("here");
        return b;
    }

}