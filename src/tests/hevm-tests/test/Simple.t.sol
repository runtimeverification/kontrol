// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import "forge-std/Test.sol";

contract SimpleTest is Test{

  // BYTECODE=$(jq .deployedBytecode.object -r out/Simple.t.sol/SimpleTest.json)

    function prove_simple(uint x) public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_simple(uint x)"
      require(x < 1);
      assert(x == 0);
    }

    function prove_revert() public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_revert()"`
      revert("Just reverts");
    }

    function prove_assertEq(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertEq(uint x)"`
      require(x < 1);
      assertEq(x, 0);
    }

    function prove_expectRevert() public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_expectRevert()"` 
      vm.expectRevert();
    }

    function prove_assertTrue(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertTrue(uint x)"`
      require(x < 1);
      assertTrue(x == 0);
    }

    function prove_assume1(uint x) public pure {
      // Fails with `hevm symbolic --code $BYTECODE --sig "prove_assume1(uint x)"`
      vm.assume(x < 1);
      assert(x != 0);
    }

    function prove_assume2(uint x) public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assume2(uint x)"`
      vm.assume(x < 1);
      assert(x == 0);
    }

    //Tests that should be failing but are passing

    function prove_assertEq_2(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertEq_2(uint x)"`
      require(x < 1);
      assertEq(x, 1);
    }

    function prove_assertFalse(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertFalse(uint x)"`
      require(x < 1);
      assertFalse(x == 0);
    }
}