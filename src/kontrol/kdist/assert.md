Kontrol Assertions
------------------
This file contains the implementation of assert cheat codes supported by Kontrol.

```k
requires "abi.md"

module KONTROL-ASSERTIONS
    imports EVM
    imports EVM-ABI
    imports FOUNDRY-ACCOUNTS
```

We define the `#assert` production together with a Bool and a String value to process assertions.
The Bool value represents the outcome of an assertion.
The String represents the error message to be returned if the assertion has failed.

```k
    syntax KItem ::= "#assert" Bool String [label(assert)]
 // ------------------------------------------------------
    rule <k> #assert true _ => .K  ... </k>
    rule <k> #assert false ERR ~> #cheatcode_return RS RW
          => #setLocalMem RS RW String2Bytes(ERR)
          ~> #refund GCALL
          ~> 0 ~> #push
          ... </k>
         <statusCode> _ => EVMC_REVERT </statusCode>
         <output> _ => String2Bytes(ERR) </output>
         <callGas> GCALL </callGas>
```

We define macros for different assert methods.
These macros expand into the `#assert` production defined earlier, providing an error message.

```k 
    syntax KItem ::= "#assert_eq" Int Int     [label(assert_eq),     macro]
                   | "#assert_ge" Int Int     [label(assert_ge),     macro]
                   | "#assert_le" Int Int     [label(assert_le),     macro]
                   | "#assert_gt" Int Int     [label(assert_gt),     macro]
                   | "#assert_lt" Int Int     [label(assert_lt),     macro]
                   | "#assert_not_eq" Int Int [label(assert_not_eq), macro]
 // -----------------------------------------------------------------------
    rule #assert_eq W1 W2     => #assert (W1 ==Int W2)  ("assertion failed: " +String Int2String(W1) +String "!=" +String Int2String(W2))
    rule #assert_ge W1 W2     => #assert (W1 >=Int W2)  ("assertion failed: " +String Int2String(W1) +String "<" +String Int2String(W2))
    rule #assert_le W1 W2     => #assert (W1 <=Int W2)  ("assertion failed: " +String Int2String(W1) +String ">" +String Int2String(W2))
    rule #assert_gt W1 W2     => #assert (W1 >Int W2)   ("assertion failed: " +String Int2String(W1) +String "<=" +String Int2String(W2))
    rule #assert_lt W1 W2     => #assert (W1 <Int W2)   ("assertion failed: " +String Int2String(W1) +String ">=" +String Int2String(W2))
    rule #assert_not_eq W1 W2 => #assert (W1 =/=Int W2) ("assertion failed: " +String Int2String(W1) +String "==" +String Int2String(W2))
```


Capturing cheat code calls
--------------------------

```k
    rule [cheatcode.call.assertEq]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ( "assertEq(uint256,uint256)" )
        orBool SELECTOR ==Int selector ( "assertEq(bool,bool)"       )
        orBool SELECTOR ==Int selector ( "assertEq(address,address)" )
        orBool SELECTOR ==Int selector ( "assertEq(bytes32,bytes32)" )
    [preserves-definedness]

    rule [cheatcode.call.assertTrue]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) bool2Word(true) ... </k>
      requires SELECTOR ==Int selector ( "assertTrue(bool)" )
    [preserves-definedness]

    rule [cheatcode.call.assertNotEq]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_not_eq #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ("assertNotEq(address,address)")
    [preserves-definedness]

    rule [cheatcode.call.assertGe]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_ge #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ("assertGe(uint256,uint256)")
    [preserves-definedness]

    rule [cheatcode.call.assertGt]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_gt #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ("assertGt(uint256,uint256)")
    [preserves-definedness]

    rule [cheatcode.call.assertLe]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_le #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ("assertLe(uint256,uint256)")
    [preserves-definedness]

    rule [cheatcode.call.assertLt]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_lt #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ("assertLt(uint256,uint256)")
    [preserves-definedness]
```

Function selectors
------------------

```k
    rule selector ( "assertEq(uint256,uint256)"    ) => 2552851540
    rule selector ( "assertEq(bool,bool)"          ) => 4160631927
    rule selector ( "assertEq(address,address)"    ) => 1364419062
    rule selector ( "assertEq(bytes32,bytes32)"    ) => 2089076379
    rule selector ( "assertTrue(bool)"             ) => 211801473
    rule selector ( "assertGe(uint256,uint256)"    ) => 2832519641
    rule selector ( "assertLe(uint256,uint256)"    ) => 2221339669
    rule selector ( "assertGt(uint256,uint256)"    ) => 3674733778
    rule selector ( "assertNotEq(address,address)" ) => 2972587668
    rule selector ( "assertLt(uint256,uint256)"    ) => 2972696581
```

```k
endmodule
```