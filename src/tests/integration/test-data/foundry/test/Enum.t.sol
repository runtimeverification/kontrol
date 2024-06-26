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


contract EnumContract {
    uint public num;
    Letter public letter;
}

contract Enum {
    EnumContract member_contract;

    function enum_storage_range() public view {
        assert(uint(member_contract.letter()) <= 5);
        assert(uint(member_contract.letter()) >= 0);
    }

}
