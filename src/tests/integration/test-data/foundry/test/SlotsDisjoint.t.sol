// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {KontrolCheats} from "kontrol-cheatcodes/KontrolCheats.sol";

contract MyERC20 {
    mapping(address account => uint256) private _balances;

    uint256 private _totalSupply;

    function totalSupply() public view virtual returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view virtual returns (uint256) {
        return _balances[account];
    }

    function transfer(address to, uint256 value) public virtual returns (bool) {
        require(to != address(0));
        require(value <= _balances[msg.sender]);

        _balances[msg.sender] -= value;
        _balances[to] += value;

        return true;
    }
}

/**
 * This test demonstrates a problem with the keccak lemmas previously present in
 * the keccak.md file, which could cause us to miss edge cases in a test. In
 * particular, the lemma
 *
 * rule [keccak-eq-conc-false]: keccak(_A)  ==Int _B => false
 *     [symbolic(_A), concrete(_B), simplification(30), comm]
 *
 * overlooks the case when _B is the keccak of a concrete value and that value
 * can be equal to _A. With this lemma, the test below passes when it shouldn´t.
 */
contract SlotsDisjointTest is Test, KontrolCheats {
    MyERC20 public token;

    function setUp() public {
        token = new MyERC20();
        kevm.symbolicStorage(address(token));
        uint256 totalSupply = freshUInt256();
        vm.store(address(token), bytes32(uint256(2)), bytes32(totalSupply));

        // Assign balance to the test contract
        uint256 balance = freshUInt256();
        bytes32 balanceAccountSlot = keccak256(abi.encode(address(this), 0));
        vm.store(address(token), balanceAccountSlot, bytes32(balance));
    }

    /**
     * This test should fail because it's possible for receiver == address(this)
     * in which case the final assertion doesn't hold. With the above lemma, we
     * miss this case and the test passes. Without the lemma, the tests fails as
     * it should.
     */
    function testReceiver(address receiver, uint256 amount) public {
        vm.assume(receiver != address(0));

        uint256 senderBalance = token.balanceOf(address(this));
        vm.assume(amount <= senderBalance);

        uint256 receiverBalance = token.balanceOf(receiver);
        vm.assume(receiverBalance <= type(uint256).max - amount);

        token.transfer(receiver, amount);

        // This should fail when receiver == address(this)
        assertEq(token.balanceOf(address(this)), senderBalance - amount);
        assertEq(token.balanceOf(receiver), receiverBalance + amount);
    }
}
