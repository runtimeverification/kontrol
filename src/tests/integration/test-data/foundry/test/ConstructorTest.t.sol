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

    function run_constructor() public {
        assert(flag);
    }
    
}
