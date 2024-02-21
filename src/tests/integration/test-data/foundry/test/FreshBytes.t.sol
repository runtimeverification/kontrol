pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "../src/KEVMCheats.sol";

contract FreshBytesTest is Test, KEVMCheats {
    bytes1 local_byte;
    bytes local_bytes;

    uint256 constant length_limit = 48;

    function manip_symbolic_bytes(bytes memory b) public {
        uint middle = b.length / 2;
        b[middle] = hex'aa';
    }

    function test_symbolic_bytes_1() public {
        uint256 length = uint256(kevm.freshUInt(1));
        vm.assume (0 < length);
        vm.assume (length <= length_limit);
        bytes memory fresh_bytes = kevm.freshBytes(length);
        uint256 index = uint256(kevm.freshUInt(1));
        vm.assume(index < length);

        local_byte = fresh_bytes[index];
        assertEq(fresh_bytes[index], local_byte);

        local_bytes = fresh_bytes;
        assertEq(fresh_bytes, local_bytes);

        manip_symbolic_bytes(fresh_bytes);
        assertEq(hex'aa', fresh_bytes[length / 2]);
    }

    function test_symbolic_bytes_length(uint256 l) public {
        vm.assume(0 < l);
        vm.assume(l <= length_limit);
        bytes memory fresh_bytes = kevm.freshBytes(l);
        assertEq(fresh_bytes.length, l);
    }
}
