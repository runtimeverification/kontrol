// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract ImmutableVarsContract {
    uint256 public immutable y;

    constructor(uint256 _y) {
        y = _y;
    }
}

contract ImmutableVarsTest is Test {
    function test_run_deployment(uint256 x) public returns (bool) {
        ImmutableVarsContract c = new ImmutableVarsContract(x);
        assert(c.y() == 85);
    }
}