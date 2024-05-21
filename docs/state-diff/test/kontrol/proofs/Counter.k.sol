// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

/* import {Test, console} from "forge-std/Test.sol"; */
/* import {Counter} from "../src/Counter.sol"; */
import {Vm} from "forge-std/Vm.sol";
import {InitialState} from "./utils/InitialState.sol";
import {ICounter as Counter} from "./utils/Interfaces.sol";

contract CounterKontrol is InitialState {
    // Cheat code address, 0x7109709ECfa91a80626fF3989D68f67F5b1DD12D
    address private constant VM_ADDRESS = address(uint160(uint256(keccak256("hevm cheat code"))));
    Vm private constant vm = Vm(VM_ADDRESS);

    Counter[] public counters;

    function setUp() public {
        counters.push(Counter(address(counter0Address)));
        counters.push(Counter(address(counter1Address)));
        counters.push(Counter(address(counter2Address)));
        counters.push(Counter(address(counter3Address)));
        counters.push(Counter(address(counter4Address)));
        counters.push(Counter(address(counter5Address)));
        counters.push(Counter(address(counter6Address)));
        counters.push(Counter(address(counter7Address)));
        counters.push(Counter(address(counter8Address)));
        counters.push(Counter(address(counter9Address)));
    }

    function prove_multiple_counters() public {
        for(uint256 i; i <= 9; ++i){
            require(counters[i].number() == i, "Bad number");
        }
    }

}
