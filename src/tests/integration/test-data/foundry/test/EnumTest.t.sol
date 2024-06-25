// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

enum Letter {
    LETTER_A,
    LETTER_B,
    LETTER_C,
    LETTER_D,
    LETTER_E,
    LETTER_F
}


contract EnumTest is Test {
    uint public num;
    string public str;
    Letter public letter;

    constructor(string memory a) payable {
        str = a;
    }
}
