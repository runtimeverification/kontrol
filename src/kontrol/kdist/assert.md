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


```k
    rule [cheatcode.call.assertEq]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ( "assertEq(uint256,uint256)" )
        orBool SELECTOR ==Int selector ( "assertEq(bool,bool)"       )
        orBool SELECTOR ==Int selector ( "assertEq(address,address)" )
        orBool SELECTOR ==Int selector ( "assertEq(bytes32,bytes32)" )
```

```k
    rule [cheatcode.call.assertTrue]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) bool2Word(true) ... </k>
      requires SELECTOR ==Int selector ( "assertTrue(bool)" )
```

Utils
-----

```k
    syntax KItem ::= "#assert_eq" Int Int [label(assert_eq)]
 // --------------------------------------------------------
    rule <k> #assert_eq W1 W2 => .K  ... </k> requires W1 ==Int W2
    rule <k> #assert_eq W1 W2 ~> #cheatcode_return RS RW
          => #setLocalMem RS RW String2Bytes("assertion failed: " +String Int2String(W1) +String "!=" +String Int2String(W2))
          ~> #refund GCALL
          ~> 0 ~> #push
          ... </k>
         <statusCode> _ => EVMC_REVERT </statusCode>
         <output> _ => String2Bytes("assertion failed: " +String Int2String(W1) +String " != " +String Int2String(W2)) </output>
         <callGas> GCALL </callGas>
    [owise]

```

Function selectors
------------------

```k
    rule selector ( "assertEq(uint256,uint256)" ) => 2552851540
    rule selector ( "assertEq(bool,bool)"       ) => 4160631927
    rule selector ( "assertEq(address,address)" ) => 1364419062
    rule selector ( "assertEq(bytes32,bytes32)" ) => 2089076379
    rule selector ( "assertTrue(bool)"          ) => 211801473
```

```k
endmodule
```