// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract DynamicTypesTest is Test {

    struct ComplexType {
        uint256 id;
        bytes content;
    }

    struct ComplexNestedType {
        ComplexType[] values;
        uint256 nonce;
    }

    struct ComplexTypeArray {
        address[] assets;
        uint256[] maxAmountsIn;
        bytes userData;
        bool fromInternalBalance;
    }

    /// @custom:kontrol-bytes-length-equals content: 10000,
    /// @custom:kontrol-array-length-equals ba: 10,
    /// @custom:kontrol-bytes-length-equals ba: 600,
    function test_complex_type(ComplexType calldata ctValues, bytes[] calldata ba) public {
        require (ba.length == 10, "DynamicTypes: invalid length for bytes[]");
        assert(ctValues.content.length == 10000);
        assert(ba[8].length == 600);
    }

    /// @custom:kontrol-array-length-equals ctValues: 10,
    /// @custom:kontrol-bytes-length-equals content: 10000,
    /// @custom:kontrol-array-length-equals ba: 10,
    /// @custom:kontrol-bytes-length-equals ba: 600,
    function test_complex_type_array(ComplexType[] calldata ctValues, bytes[] calldata ba) public {
        require (ctValues.length == 10, "DynamicTypes: invalid length for ComplexType[]");
        require (ba.length == 10, "DynamicTypes: invalid length for bytes[]");
        assert(ctValues[7].content.length == 10000);
        assert(ba[7].length == 600);
    }

    /// @custom:kontrol-array-length-equals ctValues: 10,
    /// @custom:kontrol-bytes-length-equals content: 10000,
    /// @custom:kontrol-array-length-equals ba: 10,
    /// @custom:kontrol-bytes-length-equals ba: 600,
    function test_complex_type_array_symbolic_lookup(ComplexType[] calldata ctValues, bytes[] calldata ba, uint256 offset) public {
        require (ctValues.length == 10, "DynamicTypes: invalid length for ComplexType[]");
        require (ba.length == 10, "DynamicTypes: invalid length for bytes[]");
        vm.assume(offset < 10);
        assert(ctValues[offset].content.length == 10000);
        assert(ba[offset].length == 600);
    }

    /// @custom:kontrol-array-length-equals ctValues: 10,
    /// @custom:kontrol-bytes-length-equals content: 10000,
    function test_dynamic_struct_array(ComplexType[] calldata ctValues) public {
        require (ctValues.length == 10, "DynamicTypes: invalid length for ComplexType[]");
        assert(ctValues[8].content.length == 10000);
    }

    function test_dynamic_nested_struct_array(ComplexNestedType memory cntValues) public {
        require(cntValues.values.length == 2, "DynamicTypes: invalid default length for ComplexType[] in ComplexNestedType");
    }

    function test_dynamic_struct_nested_array(ComplexTypeArray memory ctaValues) public {
        require(ctaValues.assets.length == 2, "DynamicTypes: invalid default length for assets in ComplexTypeArray");
        require(ctaValues.maxAmountsIn.length == 2, "DynamicTypes: invalid default length for maxAmountsIn in ComplexTypeArray");
    }

    function test_dynamic_byte_read(bytes memory data, uint256 offset) public {
        uint8 mydata = uint8(data[offset]);
        vm.assume(mydata < 3);
        assertTrue(mydata == 2 || mydata == 1 || mydata == 0);
    }
}
