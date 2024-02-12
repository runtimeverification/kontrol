// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

interface UIntUnaryOp {
  function applyOp(uint256 x) external view returns (uint256);
}

// CSE challenge: external function call
contract Identity is UIntUnaryOp {

    function identity(uint256 x) external pure returns (uint256) {
        return x;
    }

    function applyOp(uint256 x) external view returns (uint256) {
        return this.identity(x);
    }
}