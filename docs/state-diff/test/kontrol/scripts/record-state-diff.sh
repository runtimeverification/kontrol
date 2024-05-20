#!/bin/bash
set -euo pipefail

###########################################################################
# WARNING: This script is meant to be run from the foundry root directory #
#          ./test/kontrol/scripts/record-state-diff.sh to run it          #
###########################################################################

##########################
# ENVIRNONMENT VARIABLES #
##########################

# JSON-related variables
export STATE_DIFF_DIR=state-diff # Relative to the Foundry root directory
export STATE_DIFF_NAME=StateDiff.json
export ADDR_NAMES=AddressNames.json
CLEAN_JSON_PATH=test/kontrol/scripts/json/clean_json.py

# Where the contract and function that produces the jsons live
RECORDING_CONTRACT_DIR=test/kontrol/state-diff # Relative to the Foundry root directory
RECORDING_CONTRACT_FILE=proof-initialization.sol # Name of the Solidity file
RECORDING_CONTRACT_NAME=CounterBed # Name of the actual contract
RECORDING_CONTRACT_FUNCTION=counterBedNamed # Name of the function with the recordStateDiff modifier

RECORDING_CONTRACT_PATH="$RECORDING_CONTRACT_DIR/$RECORDING_CONTRACT_FILE:$RECORDING_CONTRACT_NAME"

# Kontrol-related variables
GENERATED_CONTRACT_NAME=InitialState
GENERATED_CONTRACT_DIR=test/kontrol/proofs/utils # Relative to the Foundry root directory
GENERATED_CONTRACT_LICENSE=UNLICENSED

####################
# RECORD EXECUTION #
####################

# Run the function with the recordStateDiff modifier
forge script $RECORDING_CONTRACT_PATH --sig "$RECORDING_CONTRACT_FUNCTION" --ffi -vvvvv
# state diff JSON comes out scaped from the last command
# We execute this script to unscape it so that it can be fed to Kontrol
python3 "$CLEAN_JSON_PATH" "$STATE_DIFF_DIR/$STATE_DIFF_NAME"

###############################
# GENERATE SOLIDITY CONTRACTS #
###############################

# Give the appropriate files to Kontrol to create the contracts
kontrol load-state-diff "$GENERATED_CONTRACT_NAME" "$STATE_DIFF_DIR/$STATE_DIFF_NAME" \
        --contract-names "$STATE_DIFF_DIR/$ADDR_NAMES" \
        --output-dir "$GENERATED_CONTRACT_DIR" \
        --license "$GENERATED_CONTRACT_LICENSE"

# Format the code to ensure compatibility with any CI checks
forge fmt "$GENERATED_CONTRACT_DIR/$GENERATED_CONTRACT_NAME.sol"
forge fmt "$GENERATED_CONTRACT_DIR/${GENERATED_CONTRACT_NAME}Code.sol"
