// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Counter} from "src/Counter.sol";
import {RecordStateDiff} from "./record-state-diff/RecordStateDiff.sol";
import {Strings} from "lib/openzeppelin-contracts/contracts/utils/Strings.sol";

contract CounterBed is RecordStateDiff {
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
            save_address(string.concat("counter", Strings.toString(i)), address(counter));
        }
    }
}
