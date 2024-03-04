pragma solidity 0.8.15;

import { Types } from "./libraries/Types.sol";

contract OptimismPortal  {

    bool paused;

    /// @notice Emitted when the pause is triggered.
    /// @param account Address of the account triggering the pause.
    event Paused(address account);

    /// @notice Emitted when the pause is lifted.
    /// @param account Address of the account triggering the unpause.
    event Unpaused(address account);

    /// @notice Reverts when paused.
    modifier whenNotPaused() {
        require(paused == false, "OptimismPortal: paused");
        _;
    }

    // TODO: supplementary function for easier verification
    function pause() external {
        paused = true;
    }

    /// @notice Proves a withdrawal transaction.
    /// @param _tx              Withdrawal transaction to finalize.
    /// @param _l2OutputIndex   L2 output index to prove against.
    /// @param _outputRootProof Inclusion proof of the L2ToL1MessagePasser contract's storage root.
    /// @param _withdrawalProof Inclusion proof of the withdrawal in L2ToL1MessagePasser contract.
    function proveWithdrawalTransaction(
        Types.WithdrawalTransaction memory _tx,
        uint256 _l2OutputIndex,
        Types.OutputRootProof calldata _outputRootProof,
        bytes[] calldata _withdrawalProof
    )
        external
        whenNotPaused
    {
    }
}
