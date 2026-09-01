// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract AssertEqDynamicTest is Test {
    function test_assert_eq_bytes_distinguishes_leading_zero() public {
        bytes memory shortValue = hex"01";
        bytes memory leadingZeroValue = hex"0001";

        assertEq(shortValue, leadingZeroValue);
    }

    function test_assert_eq_bytes_with_message_distinguishes_leading_zero() public {
        bytes memory shortValue = hex"01";
        bytes memory leadingZeroValue = hex"0001";

        assertEq(shortValue, leadingZeroValue, "different byte sequences");
    }

    function test_assert_eq_string_distinguishes_leading_zero() public {
        bytes memory shortValue = hex"01";
        bytes memory leadingZeroValue = hex"0001";

        assertEq(string(shortValue), string(leadingZeroValue));
    }

    function test_assert_eq_string_with_message_distinguishes_leading_zero() public {
        bytes memory shortValue = hex"01";
        bytes memory leadingZeroValue = hex"0001";

        assertEq(string(shortValue), string(leadingZeroValue), "different string sequences");
    }

    function test_assert_eq_equal_dynamic_values() public {
        bytes memory first = hex"0001";
        bytes memory second = hex"0001";

        assertEq(first, second);
        assertEq(first, second, "equal byte sequences");
        assertEq(string(first), string(second));
        assertEq(string(first), string(second), "equal string sequences");
    }
}
