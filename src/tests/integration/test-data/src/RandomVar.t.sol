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

    function test_randomUint(uint256 x) public view {
        vm.assume(0 < x);
        vm.assume(x <= 256);
        uint256 freshUint = vm.randomUint(x);

        assert(0 <= freshUint);
        assert(freshUint <= 2 ** x - 1);
    }

    function test_randomUint() public {
        uint256 freshUint = vm.randomUint();

        assert(0 <= freshUint);
        assert(freshUint <= 2 ** 256 - 1);
    }

    function test_randomInt(uint256 x) public view {
        vm.assume(0 < x);
        vm.assume(x <= 256);

        int256 minInt256 = -2 ** (x - 1);
        int256 maxInt256 = int256(2 ** (x - 1) - 1);

        int256 freshInt = vm.randomInt(x);

        assert(minInt256 <= freshInt);
        assert(freshInt <= maxInt256);
    }

    function test_randomInt() public view {
        int256 freshInt = vm.randomInt();

        assert(-2 ** 255 <= freshInt);
        assert(freshInt <= 2 ** 255 - 1);
    }

    function test_randomBytes_length(uint256 len) public view {
        vm.assume(0 < len);
        vm.assume(len <= length_limit);
        bytes memory freshBytes = vm.randomBytes(len);
        assertEq(freshBytes.length, len);
    }

    function test_randomBytes4_length() public view {
        bytes8 freshBytes = vm.randomBytes4();
        assertEq(freshBytes.length, 4);
    }

    function test_randomBytes8_length() public view {
        bytes8 fresh_bytes = vm.randomBytes8();
        assertEq(fresh_bytes.length, 8);
    }
}