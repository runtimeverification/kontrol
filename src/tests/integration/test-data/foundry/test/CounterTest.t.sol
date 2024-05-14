// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract Counter {
    uint256 public number;

    constructor() {
        number = 1234;
    }


    function increment() public {
        number++;
    }
}

contract CounterTest is Test, KontrolCheats {
    Counter public counter;

    function testIncrement() public {
        counter = new Counter();

        counter.increment();
        counter.increment();
        counter.increment();
        counter.increment();
        counter.increment();

        assertEq(counter.number(), 1239);
    }

}
