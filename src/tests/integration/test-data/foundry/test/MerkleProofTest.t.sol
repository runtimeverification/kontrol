// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract MerkleProofTest is Test {

    /**
     * The purpose of this test is to evaluate how well we handle branching.
     * When we assume that _validateMerkleProof holds, the execution splits
     * into 2 ** proof.length (in this case, 8) branches. We want to be able
     * to handle this amount of branching without losing information, so we
     * can still prove that it holds in the final assertTrue.
     *
     * Increase the length of the proof to evaluate scalability.
     */
    function testValidateMerkleProof(
        bytes32 leaf,
        uint256 index,
        bytes32 root,
        bytes32 proofElement0,
        bytes32 proofElement1,
        bytes32 proofElement2
    ) external {
        uint256 proofLength = 3;

        bytes32[] memory proof = new bytes32[](proofLength);
        proof[0] = proofElement0;
        proof[1] = proofElement1;
        proof[2] = proofElement2;

        vm.assume(index < 2 ** proof.length);

        vm.assume(_validateMerkleProof(leaf, index, root, proof));

        assertTrue(_validateMerkleProof(leaf, index, root, proof));
    }

    /**
     * Checks that the proof is valid for a Merkle tree with the given root
     * where the given leaf is at the given index.
     */
    function _validateMerkleProof(
        bytes32 leaf,
        uint256 index,
        bytes32 root,
        bytes32[] memory proof
    ) internal pure returns (bool) {
        // Number of leaves is exponential on the tree depth
        require(index < 2 ** proof.length);

        bytes32 hash = leaf;

        for (uint256 i; i < proof.length; i++) {
            if (index % 2 == 0) {
                // If index is even, proof element is to the right
                hash = keccak256(abi.encodePacked(hash, proof[i]));
            } else {
                // If index is odd, proof element is to the left
                hash = keccak256(abi.encodePacked(proof[i], hash));
            }

            // Go up one level in the tree
            index = index / 2;
        }

        return hash == root;
    }
}
