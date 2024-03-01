// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {console, Test} from "forge-std/Test.sol";

contract HevmTests is Test{

  // BYTECODE=$(jq .deployedBytecode.object -r out/Simple.t.sol/SimpleTest.json)

    function prove_assertEq_true(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertEq(uint)"`
      // Passes with `hevm test` 
      require(x < 1);
      assertEq(x, 0);
    }

    function prove_assertEq_false(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertEq_2(uint)"`
      // Fails with `hevm test` 
      require(x < 1);
      assertEq(x, 1);
    }

    function proveFail_assertEq(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "proveFail_assertEq_2(uint)"`
      // Passes with `hevm test`
      require(x < 1);
      assertEq(x, 1);
    }

    function prove_assertTrue(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertTrue(uint)"`
      // Passes with `hevm test`
      require(x < 1);
      assertTrue(x == 0);
    }

    function prove_assertFalse(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertFalse(uint)"`
      // Fails with `hevm test`
      require(x < 1);
      assertFalse(x == 0);
    }

    function proveFail_assertFalse(uint x) public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assertFalse(uint)"`
      // Passes with `hevm test`
      require(x < 1);
      assertFalse(x == 0);
    }

    function prove_assume_assert_true(uint x) public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_assume2(uint)"`
      // Passes with `hevm test`
      vm.assume(x < 1);
      assert(x == 0);
    }

    function prove_assume_assert_false(uint x) public pure {
      // Fails with `hevm symbolic --code $BYTECODE --sig "prove_assume1(uint)"`
      // Fails with `hevm test`
      vm.assume(x < 1);
      assert(x != 0);
    }

    function proveFail_assume_assert(uint x) public pure {
      // Fails with `hevm symbolic --code $BYTECODE --sig "proveFail_assume1(uint)"`
      // Passes with `hevm test`
      vm.assume(x < 1);
      assert(x != 0);
    }

    function prove_expectRevert() public {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_expectRevert()"`
      // Fails with `hevm test` 
      vm.expectRevert();
    }

    function prove_revert() public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_revert()"`
      // Fails with `hevm test` 
      revert("Just reverts");
    }

    function prove_require_assert_true(uint x) public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_require_assert_true(uint)"`
      // Passes with `hevm test`
      require(x < 1);
      assert(x == 0);
    }

    function prove_require_assert_false(uint x) public pure {
      // Fails with `hevm symbolic --code $BYTECODE --sig "prove_require_assert_false(uint)"`
      // Fails with `hevm test`
      require(x < 1);
      assert(x != 0);
    }

    function proveFail_require_assert(uint x) public pure {
      // Fails with `hevm symbolic --code $BYTECODE --sig "proveFail_require_assert(uint)"`
      // Passes with `hevm test`
      // Passes with `kontrol prove --match-test proveFail_require_assert`
      require(x < 1);
      assert(x != 0);
    }
    
    function prove_overflow(uint x, uint y) public pure {
      // Passes with `hevm symbolic --code $BYTECODE --sig "prove_overflow(uint, uint)"`
      // Fails with `hevm symbolic --code $BYTECODE --sig "prove_overflow(uint, uint)" --assertions '[0x01, 0x11]'` 
      uint z = x + y;
      assert(z - y == x);
    }

    function prove_divide_by_0(uint x, uint y) public pure {
      // Errors with `hevm symbolic --code $BYTECODE --sig "prove_divide_by_0(uint, uint)"`
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