pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "../src/KEVMCheats.sol";

contract FreshBytesTest is Test, KEVMCheats {
    bytes1 local_byte;
    bytes local_bytes;

    function manip_symbolic_bytes(bytes memory b) public {
        uint middle = b.length / 2;
        b[middle] = hex'aa';
    }

    function test_symbolic_bytes_1() public {
        bytes memory fresh_bytes_1 = kevm.freshBytes(5);
        local_byte = fresh_bytes_1[0];
        assertEq(fresh_bytes_1[0], local_byte);

        bytes memory fresh_bytes_2 = kevm.freshBytes(67);
        assertEq(fresh_bytes_2.length, 67);
        local_bytes = fresh_bytes_2;
        assertEq(fresh_bytes_2, local_bytes);
    }

    function test_symbolic_bytes_length(uint256 l) public {
        vm.assume(l <= 48);
        vm.assume(l > 0);
        bytes memory fresh_bytes = kevm.freshBytes(l);
        manip_symbolic_bytes(fresh_bytes);
        assertEq(hex'aa', fresh_bytes[l / 2]);
        assertEq(fresh_bytes.length, l);
    }
}
