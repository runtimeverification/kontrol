// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract EnvOrTest is Test {

    function testEnvOrUint256() public view {
        uint256 defaultValue = 42;
        uint256 value = vm.envOr("UINT256", defaultValue);
        assertEq(100, value);
    }

    function testEnvOrUint256Default() public view {
        uint256 defaultValue = 42;
        uint256 value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrUint256Bad() public view {
        uint256 defaultValue = 42;
        uint256 value = vm.envOr("BADUINT256", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrInt256() public view {
        int256 defaultValue = -42;
        int256 value = vm.envOr("INT256", defaultValue);
        assertEq(-100, value);
    }

    function testEnvOrInt256Default() public view {
        int256 defaultValue = -42;
        int256 value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrInt256Bad() public view {
        int256 defaultValue = -42;
        int256 value = vm.envOr("BADINT256", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrAddress() public view {
        address defaultValue = address(0x0);
        address value = vm.envOr("ADDRESS", defaultValue);
        assertEq(address(0x1234567890123456789012345678901234567890), value);
    }

    function testEnvOrAddressInt() public view {
        address defaultValue = address(0x0);
        address value = vm.envOr("ADDRESSINT", defaultValue);
        assertEq(address(0x7584896468543216876435687541650546890874), value);
    }
    
    function testEnvOrAddressDefault() public view {
        address defaultValue = address(0x123);
        address value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrAddressBad() public view {
        address defaultValue = address(0x123);
        address value = vm.envOr("BADADDRESS", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBytes32() public view{
        bytes32 defaultValue = bytes32("default");
        bytes32 value = vm.envOr("BYTES32", defaultValue);
        bytes32 envVarValue = 0x123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0;
        assertEq(envVarValue, value);
    }

    function testEnvOrBytes32Default() public view{
        bytes32 defaultValue = bytes32("default");
        bytes32 value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBytes32Bad() public view{
        bytes32 defaultValue = bytes32("default");
        bytes32 value = vm.envOr("BADBYTES32", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBool() public view {
        bool trueValue = vm.envOr("BOOLTRUE", false);
        assertEq(trueValue, true);
        bool falseValue = vm.envOr("BOOLFALSE", true);
        assertEq(falseValue, false);
    }

    function testEnvOrBoolDefault() public view {
        bool trueValue = vm.envOr("DEFAULT", true);
        assertEq(trueValue, true);
        bool falseValue = vm.envOr("DEFAULT", false);
        assertEq(falseValue, false);
    }

    function testEnvOrBoolBad() public view {
        bool trueValue = vm.envOr("BADBOOLTRUE", true);
        assertEq(trueValue, true);
        bool falseValue = vm.envOr("BADBOOLFALSE", false);
        assertEq(falseValue, false);
    }

    function testEnvOrBytes() public view {
        bytes memory defaultValue = "default";
        bytes memory value = vm.envOr("ANY", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrString() public view {
        string memory defaultValue = "default";
        string memory value = vm.envOr("ANY", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrUint256Array() public view {
        uint256[] memory defaultValue = new uint256[](2);
        defaultValue[0] = 1;
        defaultValue[1] = 2;
        uint256[] memory value = vm.envOr("ANY", ",", defaultValue);
        assertEq(defaultValue.length, value.length);
        for (uint256 i = 0; i < defaultValue.length; i++) {
            assertEq(defaultValue[i], value[i]);
        }
    }

    function testEnvOrStringArray() public view {
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