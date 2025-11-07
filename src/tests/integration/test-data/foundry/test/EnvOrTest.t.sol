// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract EnvOrTest is Test {

    function testEnvOrUint256() public {
        uint256 defaultValue = 42;
        uint256 value = vm.envOr("ANY", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrInt256() public {
        int256 defaultValue = -42;
        int256 value = vm.envOr("ANY", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrAddress() public {
        address defaultValue = address(0x123);
        address value = vm.envOr("ANY", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBytes32() public {
        bytes32 defaultValue = bytes32("default");
        bytes32 value = vm.envOr("ANY", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBool() public {
        bool trueValue = vm.envOr("ANY", true);
        assertEq(trueValue, true);
        bool falseValue = vm.envOr("ANY", false);
        assertEq(falseValue, false);
    }

    function testEnvOrBytes() public {
        bytes memory defaultValue = "default";
        bytes memory value = vm.envOr("ANY", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrString() public {
        string memory defaultValue = "default";
        string memory value = vm.envOr("ANY", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrUint256Array() public {
        uint256[] memory defaultValue = new uint256[](2);
        defaultValue[0] = 1;
        defaultValue[1] = 2;
        uint256[] memory value = vm.envOr("ANY", ",", defaultValue);
        assertEq(defaultValue.length, value.length);
        for (uint256 i = 0; i < defaultValue.length; i++) {
            assertEq(defaultValue[i], value[i]);
        }
    }

    function testEnvOrStringArray() public {
        string[] memory defaultValue = new string[](2);
        defaultValue[0] = "one";
        defaultValue[1] = "two";
        string[] memory value = vm.envOr("ANY", ",", defaultValue);
        assertEq(defaultValue.length, value.length);
        for (uint256 i = 0; i < defaultValue.length; i++) {
            assertEq(defaultValue[i], value[i]);
        }
    }

}