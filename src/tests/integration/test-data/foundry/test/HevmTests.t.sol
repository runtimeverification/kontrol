// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {console, Test} from "forge-std/Test.sol";

contract SimpleTest is Test{

  // BYTECODE=$(jq .deployedBytecode.object -r out/Simple.t.sol/SimpleTest.json)

    function prove_assertEq(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertEq(uint)"`
      require(x < 1);
      assertEq(x, 0);
    }

    function prove_assertEq_2(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertEq_2(uint)"`
      require(x < 1);
      assertEq(x, 1);
    }

    function prove_assertTrue(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertTrue(uint)"`
      require(x < 1);
      assertTrue(x == 0);
    }

    function prove_assertFalse(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertFalse(uint)"`
      require(x < 1);
      assertFalse(x == 0);
    }

    function prove_assume1(uint x) public pure {
      // Fails with `hevm symbolic --code $BYTECODE --sig "prove_assume1(uint)"`
      vm.assume(x < 1);
      assert(x != 0);
    }

    function prove_assume2(uint x) public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assume2(uint)"`
      vm.assume(x < 1);
      assert(x == 0);
    }

    function prove_expectRevert() public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_expectRevert()"` 
      vm.expectRevert();
    }

    function prove_revert() public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_revert()"`
      revert("Just reverts");
    }

    function prove_simple(uint x) public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_simple(uint)"`
      require(x < 1);
      assert(x == 0);
    }

    function prove_simple2(uint x) public pure {
      // Fails with `hevm symbolic --code $BYTECODE --sig "prove_simple2(uint)"`
      require(x < 1);
      //console.logBytes(abi.encodeWithSelector(0x4e487b71, 0x01));
      // 0x4e487b710000000000000000000000000000000000000000000000000000000000000001
      assert(x != 0);
    }
    
    function prove_overflow(uint x, uint y) public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_overflow(uint, uint)"`
      // Fails with `hevm symbolic --code $BYTECODE --sig "prove_overflow(uint, uint)" --assertions '[0x01, 0x11]'` 
      uint z = x + y;
      assert(z - y == x);
    }

    function prove_divide_by_0(uint x, uint y) public pure {
      // Errors with `hevm symbolic --code $BYTECODE --sig "prove_overflow(uint, uint)" --assertions '[0x01, 0x11]'`
      // Output:
      // Could not determine reachability of the following end states:
      // (Failure
      // Error:
      // ...
      uint z = x / y;
      assert(z * y <= x);
    }

    function prove_modulo_by_0(uint x, uint y) public pure {
      // Errors with `hevm symbolic --code $BYTECODE --sig "prove_overflow(uint, uint)" --assertions '[0x01, 0x11]'`
      // Output:
      // Could not determine reachability of the following end states:
      // (Failure
      // Error:
      // ...
      uint z = x % y;
      assert(z <= x);
    }
}