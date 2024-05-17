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

    modifier recordStateDiff() {
        vm.startStateDiffRecording();
        _;
        VmSafe.AccountAccess[] memory accesses = vm.stopAndReturnStateDiff();
        string memory json = LibStateDiff.encodeAccountAccesses(accesses);
        string memory statediffPath = string.concat(vm.projectRoot(), "/state-diff/StateDiff.json");
        vm.writeJson({json: json, path: statediffPath});
    }

    function save_address(string memory name, address addr) public {
        vm.writeJson({json: stdJson.serialize("", name, addr), path: "state-diff/contract-names.json"});
    }
}
