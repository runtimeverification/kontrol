// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import { UIntBinaryOp } from "./OperatorInterfaces.sol";
import { Identity } from "./Unary.sol";

// CSE challenge: storage variable of a contract type
// CSE challenge: cross-contract external function call
contract Add is UIntBinaryOp {
    Identity id;

    function applyOp(uint256 x, uint256 y) external view returns (uint256 result) {
      return id.applyOp(x) + id.applyOp(y);
    }

}

// CSE challenge: storage variable of a contract type
// CSE challenge: cross-contract external function call
contract Sub is UIntBinaryOp {
    Identity id;

    function applyOp(uint256 x, uint256 y) external view returns (uint256 result) {
      return id.applyOp(x) - id.applyOp(y);
    }
}

// CSE challenge: storage variable of a contract type
// CSE challenge: cross-contract external function call
// CSE challenge: bounded reasoning
contract Multiply is UIntBinaryOp {
    Add adder;

    function applyOp(uint256 x, uint256 y) external view returns (uint256 result) {
      for (result = 0; y > 0; y--) {
        result = adder.applyOp(result, x);
      }
    }
}
