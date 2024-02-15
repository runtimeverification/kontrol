// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "../src/Portal.sol";

contract PortalTest is Test {
    Portal portalContract;

    function setUp() public {
        portalContract = new Portal();
    }

    /// @custom:kontrol-length-equals _withdrawalProof: 3,
    /// @custom:kontrol-length-equals data: 32,
    /// @custom:kontrol-length-equals _withdrawalProof[]: 32,
    function test_withdrawal_paused(
        Types.WithdrawalTransaction calldata _tx,
        uint256 _l2OutputIndex,
        Types.OutputRootProof calldata _outputRootProof,
        bytes[] calldata _withdrawalProof
    )
        external
    {
        portalContract.pause();
        vm.expectRevert();
        portalContract.proveWithdrawalTransaction(_tx, _l2OutputIndex, _outputRootProof, _withdrawalProof);
    }
}