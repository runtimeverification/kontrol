// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "test/EnumTest.t.sol";


contract EnumTest2 is Test {
    uint public num;
    string public str;
    Letter public letter;

    constructor(string memory a) payable {
        str = a;
    }
}
