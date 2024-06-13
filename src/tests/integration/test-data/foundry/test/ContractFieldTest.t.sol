// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;
import {Test} from "forge-std/Test.sol";

contract TToken {
    uint128 private totalSupply;

    constructor(uint128 _totalSupply) {
        totalSupply = _totalSupply;
    }

    function getTotalSupply() public returns (uint256) {
      return 32 + uint256(totalSupply);
    }
}

contract TEscrow {
    TToken token;

    constructor(address _token) {
        token = TToken(_token);
    }

    function getTokenTotalSupply() public returns (uint256) {
        return token.getTotalSupply() + 13;
    }
}

contract TGovernance {
    TEscrow escrow;

    constructor(address _escrow) {
        escrow = TEscrow(_escrow);
    }

    function getEscrowTokenTotalSupply() public returns (uint256) {
        return escrow.getTokenTotalSupply();
    }
}

contract ContractFieldTest is Test {
    TToken token;
    TEscrow escrow;

    function setUp() public {
        token = new TToken(12300);
        escrow = new TEscrow(address(token));
    }

    /* Calling `getTokenTotalSupply` will summarize `totalSupply` and
       include `TestToken token` into the list of accounts in `getTokenTotalSupply`'s summary
    */
    function testEscrowToken() public {
        assert(escrow.getTokenTotalSupply() == 12345);
    }
}