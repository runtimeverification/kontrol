// SPDX-License-Identifier: UNLICENSED
// This file is meant to record state udpates with kontrol load-state (without the --from-state-diff option)
pragma solidity ^0.8.13;

import {Test} from "forge-std/Test.sol";

contract Counter {
    uint256 public number;

    function setNumber(uint256 newNumber) public {
        number = newNumber;
    }

    function increment() public {
        number++;
    }
}

// To produce the test file run from the foundry root the following command (after uncommenting vm.dumpState below):
// forge script src/ContractToRecordState.sol:RecordedCounter --sig recordExecutionWithDumpState
// And then run, from the foundry root dir:
// kontrol load-state LoadStateDump ../dumpState.json --output-dir src
contract RecordedCounter is Test {
    Counter counter1;
    Counter counter2;

    function recordExecutionWithDumpState() public {
        string memory dumpStateFile = "../dumpState.json";

        counter1 = new Counter();
        counter2 = new Counter();

        counter1.setNumber(1);
        counter2.setNumber(2);
        vm.deal(address(counter1), 1 ether);
        vm.deal(address(counter2), 2 ether);
        vm.dumpState(dumpStateFile);
    }
}