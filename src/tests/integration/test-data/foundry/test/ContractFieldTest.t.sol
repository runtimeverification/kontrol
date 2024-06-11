// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;
import {Test} from "forge-std/Test.sol";

contract TToken {
    uint128 public immutable baseSupply = 32;
    uint128 public immutable additionalSupply;

    constructor(uint128 _additionalSupply) {
        additionalSupply = _additionalSupply;
    }

    function totalSupply() public returns (uint256) {
      return uint256(baseSupply) + uint256(additionalSupply);
    }
}

contract TEscrow {
    TToken token;

    constructor(address _token) {
        token = TToken(_token);
    }

    function getTokenTotalSupply() public returns (uint256) {
        return token.totalSupply() + 23;
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