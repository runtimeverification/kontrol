// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract BlockParamsTest is Test {

    function testWarp(uint256 time) public {
        vm.warp(time);
        assertEq(block.timestamp, time);
    }

    function testRoll(uint256 newHeight) public {
        vm.roll(newHeight);
        assertEq(block.number, newHeight);
    }

    function testFee(uint256 newFee) public {
        vm.fee(newFee);
        assertEq(block.basefee, newFee);
    }

    function testChainId(uint256 newChainId) public {
        vm.chainId(newChainId);
        assertEq(block.chainid, newChainId);
    }

    function testCoinBase() public {
        address coinBase = 0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8;
        vm.coinbase(coinBase);
        assertEq(block.coinbase, coinBase);
    }

    function testBlockNumber() public {
        uint256 x = block.number;
        assert(x >= 0);
    }
}

contract RollTest is Test {
    function setUp() external {
        vm.roll(123);
    }

    // function testFail_run1() external {
    function test_roll_setup() external {
        assert(block.number == 123);

    }
}