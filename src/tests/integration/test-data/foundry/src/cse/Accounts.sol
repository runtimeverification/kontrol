// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;
import {Test} from "forge-std/Test.sol";

contract CompositionalToken {
    uint256 public totalSupply;

    constructor(uint256 _totalSupply) {
        totalSupply = _totalSupply;
    }
}

contract CompositionalEscrow {
    CompositionalToken cseToken;

    constructor(uint256 _totalSupply) {
        cseToken = new CompositionalToken(_totalSupply);
    }

    function getTokenTotalSupply() public returns (uint256) {
        return cseToken.totalSupply() + 15;
    }
}

contract CompositionalAccounts {
    CompositionalEscrow cseEscrow;

    /* Calling `getTokenTotalSupply` will summarize `totalSupply` and
       include `CompositionalEscrow escrow`and `CompositionalToken token` into the list of accounts in `getEscrowToken`'s summary
    */
    function getEscrowToken() public {
        assert(cseEscrow.getTokenTotalSupply() == 12345);
    }
}