// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

// For Simbolik contracts must be deployed to a concrete address and they must
// have concrete runtime bytecode. The purpose of this is test is to ensure
// that the initial konfiguration contains the appropiate <account> and
// <code>-cells.
contract SimbolikCode {

    uint256 number = 42;

    function getNumber() external view returns (uint256) {
        return number;
    }

}
