// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {console2 as console} from "forge-std/console2.sol";
import {stdJson} from "forge-std/StdJson.sol";
import {Vm} from "forge-std/Vm.sol";
import {VmSafe} from "forge-std/Vm.sol";
import {LibStateDiff} from "./LibStateDiff.sol";

struct Contract {
    string contractName;
    address contractAddress;
}

abstract contract RecordStateDiff {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    /// @notice Executes a function recording its state updates and saves it to the
    ///      the file $STATE_DIFF_DIR/$STATE_DIFF_FILE
    /// @dev STATE_DIFF_DIR  env var with file folder relative to the foundry root dir
    /// @dev STATE_DIFF_NAME env var with state diff file name
    modifier recordStateDiff() {
        // Check if the specified JSON file exists and create it if not
        string memory statediffFile = check_file(vm.envString("STATE_DIFF_DIR"), vm.envString("STATE_DIFF_NAME"));
        vm.startStateDiffRecording();
        _;
        VmSafe.AccountAccess[] memory accesses = vm.stopAndReturnStateDiff();
        string memory json = LibStateDiff.encodeAccountAccesses(accesses);
        vm.writeJson({json: json, path: statediffFile});
    }

    /// @notice Saves a an address with a name to $STATE_DIFF_DIR/$STATE_DIFF_NAMES
    /// @dev STATE_DIFF_DIR env var with file folder relative to the foundry root dir
    /// @dev ADDR_NAMES     env var with named addresses file name
    /// TODO: Investigate/fix why the resulting order of the strings in the json seems to not preseve the order
    ///       in which `save_address` is called when saving multiple addresses
    function save_address(address addr, string memory name) public {
        string memory address_names_file = check_file(vm.envString("STATE_DIFF_DIR"), vm.envString("ADDR_NAMES"));
        vm.writeJson({json: vm.serializeString("", vm.toString(addr), name), path: address_names_file});
    }

    /// @notice Checks if dir_name/file_name exists and creates it if not
    function check_file(string memory dir_name, string memory file_name) public returns (string memory) {
        string memory dirname = string.concat(vm.projectRoot(), "/", dir_name);
        string memory filename = string.concat(vm.projectRoot(), "/", dir_name, "/", file_name);
        if (vm.exists(filename)) return filename;
        if (!vm.isDir(dirname)) ffi_two_arg("mkdir", "-p", dirname); // Create directory if doesn't exist
        ffi_one_arg("touch", filename); // Create file. Might be redundant, but better make sure
        return filename;
    }

    /// @notice Execute one bash command with one argument
    /// @dev    Will revert if the command returns any output
    /// TODO: abstract number of arguments per function
    function ffi_one_arg(string memory command, string memory arg) public {
        string[] memory inputs = new string[](2);
        inputs[0] = command;
        inputs[1] = arg;
        bytes memory res = vm.ffi(inputs);
        require(res.length == 0, "RecordStateDiff: Command execution failed");
    }

    /// @notice Execute one bash command with one argument
    /// @dev    Will revert if the command returns any output
    /// TODO: abstract number of arguments per function
    function ffi_two_arg(string memory command, string memory arg1, string memory arg2) public {
        string[] memory inputs = new string[](3);
        inputs[0] = command;
        inputs[1] = arg1;
        inputs[2] = arg2;
        bytes memory res = vm.ffi(inputs);
        require(res.length == 0, "RecordStateDiff: Command execution failed");
    }
}
