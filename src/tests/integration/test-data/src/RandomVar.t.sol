// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";

contract RandomVarTest is Test {
    function test_randomBool() public {
        bool freshBool = vm.randomBool();
        vm.assume(freshBool);
    }

    function test_randomAddress() public {
        address fresh_address = vm.randomAddress();
        assertNotEq(fresh_address, address(this));
        assertNotEq(fresh_address, address(vm));
    }

    function test_randomUints(uint256 x) public {
        vm.assume(0 < x);
        vm.assume(x <= 256);
        uint256 freshUint = vm.randomUint(x);

        assert(0 <= freshUint);
        assert(freshUint <= 2 ** 256 - 1);
    }
}