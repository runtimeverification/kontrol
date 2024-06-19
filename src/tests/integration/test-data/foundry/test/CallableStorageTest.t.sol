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

contract CallableStorageContract {
    uint public num;
    string public str;
    Letter public letter;

    constructor(string memory a) payable {
        str = a;
    }
}

contract CallableStorageTest is Test, KontrolCheats {
    uint public a;
    CallableStorageContract member_contract;

    function setUp() public {
        member_contract = new CallableStorageContract("Test String");
    }

    function test_str() public {
        assertEq(member_contract.str(), "Test String");
    }

    function test_enum_argument_range(Letter letter) public pure {
        assert(uint(letter) <= 5);
        assert(uint(letter) >= 0);
    }

    function test_enum_storage_range() public view {
        assert(uint(member_contract.letter()) <= 5);
        assert(uint(member_contract.letter()) >= 0);
    }
}
