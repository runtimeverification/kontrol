// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

/**
 * Ensure that when using a symbolic value as a key to a mapping, Kontrol can
 * prove that the storage slot doesn't collide with other concrete slots
 * (given our assumptions and current keccak lemmas).
 */
contract SlotCollisionTest is Test {
    uint256 totalSupply;
    mapping(address => uint256) balance;

    function _balanceStorageSlot(address user) private returns (uint256) {
        uint256 baseSlot;

        assembly {
            baseSlot := balance.slot
        }

        return uint256(keccak256(abi.encode(user, baseSlot)));
    }

    function testNoCollisionWithStorageVariable(address user) public {
        vm.assume(100 < _balanceStorageSlot(user));

        balance[user] = 42;
        totalSupply = 50;

        assertEq(balance[user], 42);
    }

    function testNoCollisionWithMappingElement(address user) public {
        vm.assume(user != address(this));

        balance[user] = 42;
        balance[address(this)] = 0;

        assertEq(balance[user], 42);
    }
}
