pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "../src/KEVMCheats.sol";

contract FreshIntTest is Test, KEVMCheats {

    bytes1 local_byte;
    bytes local_bytes;

    function test_bytes() public {
        bytes memory fresh_bytes_1 = kevm.freshBytes(5);
        assertEq(fresh_bytes_1.length, 5);
        local_byte = fresh_bytes_1[0];

        bytes memory fresh_bytes_2 = kevm.freshBytes(67);
        assertEq(fresh_bytes_2.length, 67);
        local_bytes = fresh_bytes_2;
    }
}
