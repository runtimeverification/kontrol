pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "kontrol-cheatcodes/KontrolCheats.sol";

contract FreshCheatcodes is Test, KontrolCheats {
    int128 constant min = -170141183460469231731687303715884105728;
    int128 constant max = 170141183460469231731687303715884105727;

    function test_bool() public {
        bool fresh_bool = kevm.freshBool();
        if (fresh_bool){
            assertTrue(fresh_bool);
        } else {
            assertFalse(fresh_bool);
        }
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
        address fresh_address = kevm.freshAddress();
        assertNotEq(fresh_address, address(this));
        assertNotEq(fresh_address, address(vm));
    }

    function test_freshUints(uint8 x) public {
        vm.assume(0 < x);
        vm.assume(x <= 32);
        uint256 freshUint = kevm.freshUInt(x);

        assert(0 <= freshUint);
        assert(freshUint < 2 ** (8 * x));
    }

    function test_freshSymbolicWord() public {
        uint256 freshUint192 = freshUInt192();

        assert(0 <= freshUint192);
        assert(freshUint192 <= type(uint192).max);
    }

    function test_custom_names() public {
        bool x = kevm.freshBool("BOOLEAN");
        bool y = kevm.freshBool("BOOLEAN");
        vm.assume(x == true);
        vm.assume(y == false);
        uint256 slot = freshUInt256("NEW_SLOT");
        address new_account = kevm.freshAddress("NEW_ACCOUNT");
        kevm.setArbitraryStorage(new_account, "NEW_ACCOUNT_STORAGE");
        bytes memory value = kevm.freshBytes(32, "NEW_BYTES");
        vm.store(new_account, bytes32(slot), bytes32(value));
    }
}
