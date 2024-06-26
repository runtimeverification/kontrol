// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

enum Letter {
    LETTER_A,
    LETTER_B,
    LETTER_C,
    LETTER_D,
    LETTER_E,
    LETTER_F
}

contract EnumContract {
    uint256 public count;
    Letter public letter;

    constructor() payable {
        count = 5;
    }
}

contract Enum {
    EnumContract member_contract;

    function enum_storage_range() public view {
        assert(uint(member_contract.letter()) <= 5);
        assert(uint(member_contract.letter()) >= 0);
    }

}
