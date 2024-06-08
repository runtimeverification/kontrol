// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;
import {Test} from "forge-std/Test.sol";

contract TestToken {
    uint256 public totalSupply;

    constructor(uint256 _totalSupply) {
        totalSupply = _totalSupply;
    }
}

contract Escrow {
    TestToken token;
    uint256 tokenTotalSupply;

    constructor(uint256 _totalSupply) {
        token = new TestToken(_totalSupply);
    }

    function getTokenTotalSupply() public returns (uint256) {
        return token.totalSupply() + 15;
    }
}

contract ContractFieldTest is Test {
    Escrow escrow;

    function setUp() public {
        escrow = new Escrow(12330);
    }

    /* Calling `getTokenTotalSupply` will summarize `totalSupply` and
       include `TestToken token` into the list of accounts in `getTokenTotalSupply`'s summary
    */
    function testEscrowToken() public {
        assert(escrow.getTokenTotalSupply() == 12345);
    }
}