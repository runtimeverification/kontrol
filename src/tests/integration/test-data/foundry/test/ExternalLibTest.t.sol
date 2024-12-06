// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

library SimpleMath {
    struct LibStruct {
        uint256 elementOne;
        address elementTwo;
    }

    function structInput(LibStruct memory s) public pure returns (uint256) {
        return s.elementOne;
    }

    function square(uint256 x) public pure returns (uint256) {
        return x * x;
    }
}

contract ExternalLibTest is Test {
    function testSquare(uint256 n) public view {
        vm.assume(msg.sender == address(110));
        vm.assume(n <= type(uint128).max);
        assertEq(SimpleMath.square(n), n * n);
    }
}
