// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract BlockParamsTest is Test {

    function test_block_params(uint256 time, uint256 newHeight, uint256 newFee, uint256 newChainId, address coinBase) public {
        vm.warp(time);
        assertEq(block.timestamp, time);
        vm.roll(newHeight);
        assertEq(block.number, newHeight);
        vm.fee(newFee);
        assertEq(block.basefee, newFee);
        vm.chainId(newChainId);
        assertEq(block.chainid, newChainId);
        vm.coinbase(coinBase);
        assertEq(block.coinbase, coinBase);
    }

    function testBlockNumber() public view {
        uint256 x = block.number;
        assert(x >= 0);
    }
}

contract BlockParamsSetupTest is Test {
    function setUp() external {
        vm.roll(123);
        vm.warp(1641070800);
        vm.fee(25 gwei);
        vm.chainId(31337);
        vm.coinbase(0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8);
    }

    function test_block_params_setup() external view {
        assert(block.number == 123);
        assert(block.timestamp == 1641070800);
        assert(block.basefee == 25 gwei);
        assert(block.chainid == 31337);
        assert(block.coinbase == 0xEA674fdDe714fd979de3EdF0F56AA9716B898ec8);
    }
}
