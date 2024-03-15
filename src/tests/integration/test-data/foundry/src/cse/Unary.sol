// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import { UIntUnaryOp } from "./OperatorInterfaces.sol";

// CSE challenge: external function call
contract Identity is UIntUnaryOp {

    function identity(uint256 x) external pure returns (uint256) {
        return x;
    }

    function applyOp(uint256 x) external view returns (uint256) {
        return this.identity(x);
    }
}

// CSE challenge: storage variable of a basic type
contract AddConst is UIntUnaryOp {
    uint256 c;

    function setConst(uint256 x) external {
        c = x;
    }

    function applyOp(uint256 x) external view returns (uint256) {
        return x + c;
    }
}

// CSE challenge: storage variable of an interface type
//                this is higher-order and not possible in general
//                one way of handling this is instantiating the `UIntUnaryOp`
//                interface with specific contracts that implement it
// CSE challenge: cross-contract external function call
contract Iterate is UIntUnaryOp {
    UIntUnaryOp f;

    function applyOp(uint256 x) external view returns (uint256) {
        return f.applyOp((f.applyOp(x)));
    }
}