pragma solidity =0.8.13;

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
    event WithdrawalProven(address indexed from, address indexed to);

    /// @notice Reverts when paused.
    modifier whenNotPaused() {
        require(paused == false, "Portal: paused");
        _;
    }

    constructor() {
        paused = true;
    }

    /// @notice Proves a withdrawal transaction.
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
