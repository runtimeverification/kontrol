// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract ConstructorTest is Test {
    bool flag = true;

    function test_constructor() public {
        assert(flag);
    }

    function testFail_constructor() public {
        assert(!flag);
    }

    function get_flag() public returns (bool) {
        return flag;
    }

    function test_run_constructor() public {
        assert(get_flag());
    }

    function testFail_run_constructor() public {
        assert(!get_flag());
    }

}
