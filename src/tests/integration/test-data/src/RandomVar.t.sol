// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";

contract RandomVarTest is Test {
    uint256 constant length_limit = 72;

    function test_randomBool() public view {
        bool freshBool = vm.randomBool();
        vm.assume(freshBool);
    }

    function test_randomAddress() public {
        address freshAddress = vm.randomAddress();
        assertNotEq(freshAddress, address(this));
        assertNotEq(freshAddress, address(vm));
    }

    function test_randomBytes_length(uint256 len) public view {
        vm.assume(0 < len);
        vm.assume(len <= length_limit);
        bytes memory freshBytes = vm.randomBytes(len);
        assertEq(freshBytes.length, len);
    }

    function test_randomBytes4_length() public view {
        bytes4 freshBytes = vm.randomBytes4();
        assertEq(freshBytes.length, 4);
    }

    function test_randomBytes8_length() public view {
        bytes8 freshBytes = vm.randomBytes8();
        assertEq(freshBytes.length, 8);
    }

    function test_randomUint_192() public {
        uint256 randomUint192 = vm.randomUint(192);

        assert(0 <= randomUint192);
        assert(randomUint192 <= type(uint192).max);
    }

    function test_randomUint_Range(uint256 min, uint256 max) public {
        vm.assume(max >= min);
        uint256 rand = vm.randomUint(min, max);
        assertTrue(rand >= min, "rand >= min");
        assertTrue(rand <= max, "rand <= max");
    }

    function test_randomUint() public {
        uint256 rand = vm.randomUint();
        assertTrue(rand >= type(uint256).min);
        assertTrue(rand <= type(uint256).max);
    }
}