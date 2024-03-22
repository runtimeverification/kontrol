pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "kontrol-cheatcodes/KontrolCheats.sol";

contract FreshCheatcodes is Test, KontrolCheats {
    int128 constant min = -170141183460469231731687303715884105728;
    int128 constant max = 170141183460469231731687303715884105727;

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

    function test_address() public {
        uint256 fresh_address = uint160(kevm.freshAddress());
        assertGe(fresh_address, type(uint160).min);
        assertLe(fresh_address, type(uint160).max);
    }

    function test_freshUints(uint8 x) public {
        uint256 freshUint = kevm.freshUInt(x);

        assert(0 <= freshUint);
        assert(freshUint < 2 ** (8 * x));
    }

    function test_freshSymbolicWord() public {
        uint256 freshUint192 = freshUInt192();

        assert(0 <= freshUint192);
        assert(freshUint192 < type(uint192).max);
    }
}
