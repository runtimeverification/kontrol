// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;
import {Test} from "forge-std/Test.sol";

contract Token {
    uint256 public totalSupply;
    
    constructor(uint256 _totalSupply) {
        totalSupply = _totalSupply;
    }
}

contract Escrow {
    Token token;
    uint256 tokenTotalSupply;

    function getTokenTotalSupply() public {
        uint256 tokenTS = token.totalSupply();
        tokenTotalSupply = tokenTS + 15;
    }
}

contract ContractFieldTest is Test {
    Escrow escrow; 

    function setUp() public {
        escrow = new Escrow();
    }

    /* Calling `getTokenTotalSupply` will summarize `totalSupply` and
       include `Token token` into the list of accounts in `getTokenTotalSupply`'s summary
    */
    function testEscrowToken() public {
        escrow.getTokenTotalSupply();
    }
}