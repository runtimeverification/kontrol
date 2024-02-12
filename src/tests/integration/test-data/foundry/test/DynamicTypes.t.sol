// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract DynamicTypesTest is Test {

    struct ComplexType {
        uint256 id;
        bytes content;
    }

    /// @custom:kontrol-length-equals content: 10000,
    /// @custom:kontrol-length-equals ba: 10,
    /// @custom:kontrol-length-equals ba[]:600,
    function test_complex_type(ComplexType calldata ctValues, bytes[] calldata ba) public {
        require (ba.length == 10, "DynamicTypes: invalid length for bytes[]");
        assert(ctValues.content.length == 10000);
        assert(ba[8].length == 600);
    }

    /// @custom:kontrol-length-equals ctValues: 10,
    /// @custom:kontrol-length-equals content: 10000,
    /// @custom:kontrol-length-equals ba: 10,
    /// @custom:kontrol-length-equals ba[]:600,
    function test_complex_type_array(ComplexType[] calldata ctValues, bytes[] calldata ba, uint256 offset) public {
        require (ctValues.length == 10, "DynamicTypes: invalid length for ComplexType[]");
        require (ba.length == 10, "DynamicTypes: invalid length for bytes[]");
        vm.assume(offset < 10);
        assert(ctValues[offset].content.length == 10000);
        assert(ba[offset].length == 600);
    }

    function test_dynamic_byte_read(bytes memory data, uint256 offset) public {
        uint8 mydata = uint8(data[offset]);
        vm.assume(mydata < 3);
        assertTrue(mydata == 2 || mydata == 1 || mydata == 0);
    }
}
