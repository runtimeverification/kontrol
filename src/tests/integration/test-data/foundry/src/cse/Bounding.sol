// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

interface UIntBinaryOp {
  function applyOp(uint256 x, uint256 y) external pure returns (uint256 result);
}

// CSE challenge: bounded reasoning
contract Multiply is UIntBinaryOp {

    function applyOp(uint256 x, uint256 y) external pure returns (uint256 result) {
      for (result = 0; y > 0; y--) {
        result += x;
      }
    }
}
