pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "kontrol-cheatcodes/KontrolCheats.sol";

contract FreshCheatcodes is Test, KontrolCheats {
    int128 constant min = -170141183460469231731687303715884105728;
    int128 constant max = 170141183460469231731687303715884105727;

    function test_bool() public view {
        bool fresh_bool = kevm.freshBool();
        if (fresh_bool){
            assertTrue(fresh_bool);
        } else {
            assertFalse(fresh_bool);
        }
    }

    function test_int128() public view {
        int128 val = int128(uint128(kevm.freshUInt(16)));
        assert(val >= min);
        assert(val <= max);
    }

    function testFail_int128() public view {
        int128 val = int128(uint128(kevm.freshUInt(16)));
        assertGt(val, max);
    }

    function test_address() public view {
        address fresh_address = kevm.freshAddress();
        assertNotEq(fresh_address, address(this));
        assertNotEq(fresh_address, address(vm));
    }

    function test_freshUints(uint8 x) public view {
        vm.assume(0 < x);
        vm.assume(x <= 32);
        uint256 freshUint = kevm.freshUInt(x);

        assert(0 <= freshUint);
        assert(freshUint < 2 ** (8 * x));
    }

    function test_freshSymbolicWord() public view {
        uint256 freshUint192 = freshUInt192();

        assert(0 <= freshUint192);
        assert(freshUint192 <= type(uint192).max);
    }
}
