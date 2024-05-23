// SPDX-License-Identifier: UNLICENSED

pragma solidity ^0.8.13;

interface ICounter {
    function number() external returns (uint256);

    function setNumber(uint256) external;

    function increment(uint256) external;
}
