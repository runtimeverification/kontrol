// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test} from "forge-std/Test.sol";
import {Counter} from "src/Counter.sol";
import {RecordStateDiff} from "./record-state-diff/RecordStateDiff.sol";

contract CounterBed is Test, RecordStateDiff {
    Counter public counter;

    function counterBed() public recordStateDiff {
        for (uint8 i; i <= 9; ++i) {
            counter = new Counter();
            counter.setNumber(i);
        }
    }

    function counterBedNamed() public recordStateDiff {
        for (uint8 i; i <= 9; ++i) {
            counter = new Counter();
            counter.setNumber(i);
            save_address(string.concat("counter", vm.toString(i)), address(counter));
        }
    }
}
