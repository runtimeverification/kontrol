// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract IdentityContract {

    function identity(uint256 x) external pure returns (uint256) {
        return x;
    }

    function identity_wrapper(uint256 x) external returns (uint256) {
        return this.identity_wrapper(x);
    }
}

contract DoubleContract {

    IdentityContract id;

    constructor() {
      id = new IdentityContract();
    }

    function double(uint256 x) external returns (uint256) {
        return id.identity(x) + id.identity_wrapper((x));
    }
}
