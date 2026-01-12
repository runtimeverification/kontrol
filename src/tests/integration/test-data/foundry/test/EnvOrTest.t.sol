// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract EnvOrTest is Test {

    function testEnvOrUint256() public  {
        uint256 defaultValue = 42;
        uint256 value = vm.envOr("UINT256", defaultValue);
        assertEq(100, value);
    }

    function testEnvOrUint256Default() public  {
        uint256 defaultValue = 42;
        uint256 value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrUint256Bad() public  {
        uint256 defaultValue = 42;
        uint256 value = vm.envOr("BADUINT256", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrInt256() public  {
        int256 defaultValue = -42;
        int256 value = vm.envOr("INT256", defaultValue);
        assertEq(-100, value);
    }

    function testEnvOrInt256Default() public  {
        int256 defaultValue = -42;
        int256 value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrInt256Bad() public  {
        int256 defaultValue = -42;
        int256 value = vm.envOr("BADINT256", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrAddress() public  {
        address defaultValue = address(0x0);
        address value = vm.envOr("ADDRESS", defaultValue);
        assertEq(address(0x1234567890123456789012345678901234567890), value);
    }

    function testEnvOrAddressInt() public  {
        address defaultValue = address(0x0);
        address value = vm.envOr("ADDRESSINT", defaultValue);
        assertEq(address(0x7584896468543216876435687541650546890874), value);
    }
    
    function testEnvOrAddressDefault() public  {
        address defaultValue = address(0x123);
        address value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrAddressBad() public  {
        address defaultValue = address(0x123);
        address value = vm.envOr("BADADDRESS", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBytes32() public {
        bytes32 defaultValue = bytes32("default");
        bytes32 value = vm.envOr("BYTES32", defaultValue);
        bytes32 envVarValue = 0x123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0;
        assertEq(envVarValue, value);
    }

    function testEnvOrBytes32Default() public {
        bytes32 defaultValue = bytes32("default");
        bytes32 value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBytes32Bad() public {
        bytes32 defaultValue = bytes32("default");
        bytes32 value = vm.envOr("BADBYTES32", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBool() public  {
        bool trueValue = vm.envOr("BOOLTRUE", false);
        assertEq(trueValue, true);
        bool falseValue = vm.envOr("BOOLFALSE", true);
        assertEq(falseValue, false);
    }

    function testEnvOrBoolDefault() public  {
        bool trueValue = vm.envOr("DEFAULT", true);
        assertEq(trueValue, true);
        bool falseValue = vm.envOr("DEFAULT", false);
        assertEq(falseValue, false);
    }

    function testEnvOrBoolBad() public  {
        bool trueValue = vm.envOr("BADBOOLTRUE", true);
        assertEq(trueValue, true);
        bool falseValue = vm.envOr("BADBOOLFALSE", false);
        assertEq(falseValue, false);
    }

    function testEnvOrBytes() public  {
        bytes memory defaultValue = "default";
        bytes memory value = vm.envOr("BYTES", defaultValue);
        bytes memory expectedValue = hex"deadbeef";
        assertEq(expectedValue, value);
    }

    function testEnvOrBytesDefault() public  {
        bytes memory defaultValue = "default";
        bytes memory value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrBytesBad() public  {
        bytes memory defaultValue = "default";
        bytes memory value = vm.envOr("BADBYTES", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrString() public  {
        string memory defaultValue = "default";
        string memory value = vm.envOr("STRING", defaultValue);
        assertEq("hello_world", value);
    }

    function testEnvOrStringDefault() public  {
        string memory defaultValue = "default";
        string memory value = vm.envOr("DEFAULT", defaultValue);
        assertEq(defaultValue, value);
    }

    function testEnvOrArrayUint256() public {
        uint256[] memory defaultValue = new uint256[](2);
        defaultValue[0] = 6;
        defaultValue[1] = 7;
        uint256[] memory value = vm.envOr("UINT256ARRAY", ",", defaultValue);
        assertEq(5, value.length);
        for (uint256 i = 0; i < 5; i++) {
            assertEq(i, value[i]);
        }
    }

    function testEnvOrArrayUint256Default() public {
        uint256[] memory defaultValue = new uint256[](2);
        defaultValue[0] = 1;
        defaultValue[1] = 2;
        uint256[] memory value = vm.envOr("DEFAULT", ",", defaultValue);
        assertEq(defaultValue.length, value.length);
        for (uint256 i = 0; i < defaultValue.length; i++) {
            assertEq(defaultValue[i], value[i]);
        }
    }

    function testEnvOrArrayInt256() public {
        int256[] memory defaultValue = new int256[](2);
        defaultValue[0] = -6;
        defaultValue[1] = -7;
        int256[] memory value = vm.envOr("INT256ARRAY", ",", defaultValue);
        assertEq(5, value.length);
        for (uint256 i = 0; i < 5; i++) {
            assertEq(int256(i), value[i]+2);
        }
    }

    function testEnvOrArrayAddress() public {
        address[] memory defaultValue = new address[](2);
        defaultValue[0] = address(0x1);
        defaultValue[1] = address(0x2);
        address[] memory value = vm.envOr("ADDRESSARRAY", ",", defaultValue);
        assertEq(3, value.length);
        assertEq(address(0x1234567890123456789012345678901234567890), value[0]);
        assertEq(address(0x2345678901234567890123456789012345678901), value[1]);
        assertEq(address(0x3456789012345678901234567890123456789012), value[2]);
    }

    function testEnvOrArrayBytes32() public {
        bytes32[] memory defaultValue = new bytes32[](2);
        defaultValue[0] = bytes32("one");
        defaultValue[1] = bytes32("two");
        bytes32[] memory value = vm.envOr("BYTES32ARRAY", ",", defaultValue);
        assertEq(3, value.length);
        assertEq(0x123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0, value[0]);
        assertEq(0x15864864541fe8548484c8548654189d4184864a48618c54615156d165651f65, value[1]);
        assertEq(0x7468697264d18561e8691a891968f189868c18969d1868641f1818861685a189, value[2]);
    }

    function testEnvOrArrayBool() public {
        bool[] memory defaultValue = new bool[](2);
        defaultValue[0] = true;
        defaultValue[1] = false;
        bool[] memory value = vm.envOr("BOOLARRAY", ",", defaultValue);
        assertEq(4, value.length);
        assertEq(true, value[0]);
        assertEq(false, value[1]);
        assertEq(true, value[2]);
        assertEq(false, value[3]);
    }

    function testEnvOrArrayString() public {
        string[] memory defaultValue = new string[](0);
        string[] memory retrievedValue = new string[](2);
        retrievedValue[0] = "one";
        retrievedValue[1] = "two";
        string[] memory value = vm.envOr("STRINGARRAY", ",", defaultValue);
        //assertEq(retrievedValue.length, value.length);
        for (uint256 i = 0; i < retrievedValue.length; i++) {
            assertEq(retrievedValue[i], value[i]);
        }
    }

    function testEnvOrArrayStringDefault() public {
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