// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract Counter {
    uint256 public number;

    function setNumber(uint256 newNumber) public {
        number = newNumber;
    }

    function increment() public {
        number++;
    }
}

contract CounterTest is Test, KontrolCheats {
    Counter public counter;
    
    // function setUp() public {
    //     counter = new Counter();
    //     counter.setNumber(0);
    // }

    function testIncrement() public {
        counter = new Counter();
        counter.setNumber(0);
        counter.increment();
        assertEq(counter.number(), 1);
    }

    function testSetNumber(uint256 x) public {
        //setUp();
        counter = new Counter();
        counter.setNumber(0);
        counter.setNumber(x);
        assertEq(counter.number(), x);
    }
}