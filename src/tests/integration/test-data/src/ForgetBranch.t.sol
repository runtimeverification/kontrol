// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.13;

import {Test, console} from "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";


contract ForgetBranchTest is Test, KontrolCheats {

    function test_forgetBranch(uint256 x) public {
        uint256 y;

        vm.assume(x > 200);
        kevm.forgetBranch(200, KontrolCheatsBase.ComparisonOperator.GreaterThan, x);
        if(x > 200){
            y = 21;
        } else {
            y = 42;
        }
    }
}