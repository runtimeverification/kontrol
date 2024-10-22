// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;


// CSE challenge: multiple branches that slow down the verification
contract Branches{
    function applyOp(uint256 x, uint256 y, bool z) public returns (uint256) {
      if (z) {
        return x + y;
      } else {
        return x * y;
      }
    }
}