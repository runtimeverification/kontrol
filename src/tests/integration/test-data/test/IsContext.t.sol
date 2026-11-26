// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";
import {VmSafe} from "forge-std/Vm.sol";

contract IsContextTest is Test {
    function test_isContext_testGroup() public view {
        assertTrue(vm.isContext(VmSafe.ForgeContext.TestGroup));
        assertTrue(vm.isContext(VmSafe.ForgeContext.Test));
    }

    function test_isContext_otherContexts() public view {
        assertFalse(vm.isContext(VmSafe.ForgeContext.Coverage));
        assertFalse(vm.isContext(VmSafe.ForgeContext.Snapshot));
        assertFalse(vm.isContext(VmSafe.ForgeContext.ScriptGroup));
        assertFalse(vm.isContext(VmSafe.ForgeContext.ScriptDryRun));
        assertFalse(vm.isContext(VmSafe.ForgeContext.ScriptBroadcast));
        assertFalse(vm.isContext(VmSafe.ForgeContext.ScriptResume));
        assertFalse(vm.isContext(VmSafe.ForgeContext.Unknown));
    }

    function test_isContext_symbolic(uint8 context) public view {
        vm.assume(context <= uint8(VmSafe.ForgeContext.Unknown));
        assertEq(vm.isContext(VmSafe.ForgeContext(context)), context <= uint8(VmSafe.ForgeContext.Test));
    }
}
