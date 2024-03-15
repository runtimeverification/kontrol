// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

interface UIntUnaryOp {
  function applyOp(uint256 x) external view returns (uint256);
}

interface UIntBinaryOp {
  function applyOp(uint256 x, uint256 y) external view returns (uint256 result);
}
