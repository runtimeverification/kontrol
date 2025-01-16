// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract ValueStore {
	uint256 public slot0;
	uint256 public slot1;

	function changeSlot0(uint256 newValue) public {
		slot0 = newValue;
	}

	function changeSlot1(uint256 newValue) public {
		slot1 = newValue;
	}
}

contract AllowChangesTest is Test, KontrolCheats {
	ValueStore canChange;
	ValueStore cannotChange;	
	
	function setUp() public {
		canChange = new ValueStore();
		cannotChange = new ValueStore();
	}

	function testAllowCalls(uint256 value) public {
		/* Whitelisting two calls to ensure that `allowCalls` is working
			for whitelist with > 1 elements */
		bytes memory changeCallDataOne = abi.encodeWithSelector(
			ValueStore.changeSlot0.selector,
			value
		);

		bytes memory changeCallDataTwo = abi.encodeWithSelector(
			ValueStore.changeSlot1.selector,
			value
		);

		kevm.allowCalls(address(canChange), changeCallDataOne);
		kevm.allowCalls(address(canChange), changeCallDataTwo);

		canChange.changeSlot0(value);
	}

	function testFailAllowCalls_ifNotWhitelisted(uint256 value) public {
		bytes memory changeCallData = abi.encodeWithSelector(
			ValueStore.changeSlot0.selector,
			value
		);

		kevm.allowCalls(address(canChange), changeCallData);

		canChange.changeSlot1(value);
	}
}