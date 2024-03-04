pragma solidity ^0.8.13;

import { Vm } from "lib/forge-std/src/Vm.sol";
import { Types } from "src/libraries/Types.sol";

import { OptimismPortal } from "../src/OptimismPortal.sol";

contract OptimismPortalKontrol {
    address private constant VM_ADDRESS = address(uint160(uint256(keccak256("hevm cheat code"))));
    Vm private constant vm = Vm(VM_ADDRESS);
    OptimismPortal optimismPortal;

    function setUp() public{
        optimismPortal = new OptimismPortal();
    }

    /// @custom:kontrol-array-length-equals _withdrawalProof: 2,
    /// @custom:kontrol-bytes-length-equals _withdrawalProof: 32,
    function test_finalizeWithdrawalTransaction_paused(
        Types.WithdrawalTransaction memory _tx,
        uint256 _l2OutputIndex,
        Types.OutputRootProof calldata _outputRootProof,
        bytes[] calldata _withdrawalProof
    )
        external
    {
        optimismPortal.pause();

        vm.expectRevert();
        optimismPortal.proveWithdrawalTransaction(_tx, _l2OutputIndex, _outputRootProof, _withdrawalProof);
    }
}

