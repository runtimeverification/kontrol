// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract CallableStorageContract {
    uint public num;
    string public str;
    uint immutable imm;

    constructor(string memory a) payable {
        str = a;
        imm = 2;
    }

    function doNothing() public {
        return;
    }
}

contract CallableStorageTest is Test, KontrolCheats {
    CallableStorageContract member_contract;

    function setUp() public {
        member_contract = new CallableStorageContract("Test String");
    }

    function test_str_callable() public {
        assertEq(member_contract.str(), "Test String");
    }
}
