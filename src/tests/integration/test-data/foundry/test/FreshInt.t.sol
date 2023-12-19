pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "../src/KEVMCheats.sol";

contract FreshIntTest is Test, KEVMCheats {
    int128 constant min = -170141183460469231731687303715884105728;
    int128 constant max = 170141183460469231731687303715884105727;

    bytes1 local_byte;
    bytes local_bytes;

    function test_uint128() public {
        uint256 fresh_uint128 = uint256(kevm.freshUInt(32));
        assertGe(fresh_uint128, type(uint128).min);
        assertLe(fresh_uint128, type(uint128).max);
    }

    function test_bool() public {
        uint256 fresh_uint256 = kevm.freshBool();
        assertGe(fresh_uint256, 0);
        assertLe(fresh_uint256, 1);
    }

    function test_int128() public {
        int128 val = int128(uint128(kevm.freshUInt(16)));
        assertGe(val, min);
        assertLe(val, max);
    }

    function testFail_int128() public {
        int128 val = int128(uint128(kevm.freshUInt(16)));
        assertGt(val, max);
    }

    function test_bytes() public {
        bytes memory fresh_bytes_1 = kevm.freshBytes(5);
        assertEq(fresh_bytes_1.length, 5);
        local_byte = fresh_bytes_1[0];

        bytes memory fresh_bytes_2 = kevm.freshBytes(67);
        assertEq(fresh_bytes_2.length, 67);
        local_bytes = fresh_bytes_2;
    }
}
