// SPDX-License-Identifier: UNLICENSED
// This file was autogenerated by running `kontrol load-state`. Do not edit this file manually.

pragma solidity ^0.8.13;

import { Vm } from "forge-std/Vm.sol";

import { LoadStateDiffCode } from "./LoadStateDiffCode.sol";

contract LoadStateDiff is LoadStateDiffCode {
	// Cheat code address, 0x7109709ECfa91a80626fF3989D68f67F5b1DD12D
	address private constant VM_ADDRESS = address(uint160(uint256(keccak256("hevm cheat code"))));
	Vm private constant vm = Vm(VM_ADDRESS);

	address internal constant acc0Address = 0x5615dEB798BB3E4dFa0139dFa1b3D433Cc23b72f;


	function recreateState() public {
		bytes32 slot;
		bytes32 value;
		vm.etch(acc0Address, acc0Code);
		slot = hex'0000000000000000000000000000000000000000000000000000000000000000';
		value = hex'0000000000000000000000000000000000000000000000000000000000000003';
		vm.store(acc0Address, slot, value);
	}
}