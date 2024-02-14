pragma solidity ^0.8.13;

library Types {
    struct OutputRootProof {
        bytes32 version;
        bytes32 stateRoot;
        bytes32 messagePasserStorageRoot;
        bytes32 latestBlockhash;
    }

    struct WithdrawalTransaction {
        uint256 nonce;
        address sender;
        address target;
        uint256 value;
        uint256 gasLimit;
        bytes data;
    }
}

contract Portal  {
    bool paused;

    /// @notice Emitted when a withdrawal transaction is proven.
    /// @param from           Address that triggered the withdrawal transaction.
    /// @param to             Address that the withdrawal transaction is directed to.
    event WithdrawalProven(address indexed from, address indexed to);

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
        // Emit a `WithdrawalProven` event.
        emit WithdrawalProven(_tx.sender, _tx.target);
    }
}
