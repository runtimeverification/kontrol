// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";


contract Precondition {
    /// @custom:kontrol-precondition x >= 2,
    function totalSupply(uint256 x) public pure returns (uint256) { return x; }
}

contract PreconditionTest is  Test {
    uint256 targetValue;

    function setUp() public {
        targetValue = vm.randomUint();
    }

     /// @custom:kontrol-precondition x <= 7 * 2,
    function testPrecondition(uint256 x) public {
        Precondition p = new Precondition();
        uint256 r = p.totalSupply(x);
        assert(r <= 14);
    }

     /// @custom:kontrol-precondition _account != msg.sender,
     /// @custom:kontrol-precondition block.number == 25252525,
     /// @custom:kontrol-precondition value % 2 == 0,
    function testPrecondition_globalVariables(uint256 value, address _account) public view {
        assert (block.number == 25252525);
        assert (_account != msg.sender);
        assert ( value % 2 == 0);
    }

     /// @custom:kontrol-precondition _account == 0xfffff0 || _account == 0xfffff1,
    function testPrecondition_hexLiterals(address _account) public pure {
        assert (_account != address(0xfffffa));
    }

     /// @custom:kontrol-precondition targetValue == 6 ether,
    function testPrecondition_storage() public view{
        assert(targetValue == 6 ether);
    }
}
