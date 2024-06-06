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

We define the `#assert` production together with a Bool and a Bytes value to process assertions.
The Bool value represents the outcome of an assertion.
The Bytes represents the error message to be returned if the assertion has failed.

```k
    syntax KItem ::= "#assert" Bool Bytes [label(assert)]
 // -----------------------------------------------------
    rule <k> #assert true _ => .K  ... </k>
    rule <k> #assert false ERR ~> #cheatcode_return RS RW
          => #setLocalMem RS RW ERR
          ~> #refund GCALL
          ~> 0 ~> #push
          ... </k>
         <statusCode> _ => EVMC_REVERT </statusCode>
         <output> _ => ERR </output>
         <callGas> GCALL </callGas>
```

We define macros for different assert methods.
These macros expand into the `#assert` production defined earlier, providing an error message.

```k
    syntax KItem ::= "#assert_eq" Int Int Bytes                [label(assert_eq),     macro]
                   | "#assert_ge" Int Int Bytes                [label(assert_ge),     macro]
                   | "#assert_gt" Int Int Bytes                [label(assert_gt),     macro]
                   | "#assert_le" Int Int Bytes                [label(assert_le),     macro]
                   | "#assert_lt" Int Int Bytes                [label(assert_lt),     macro]
                   | "#assert_not_eq" Int Int Bytes            [label(assert_not_eq), macro]
                   | "#assert_approx_eq_abs" Int Int Int Bytes [label(assert_approx_eq_abs), macro]
                   | "#assert_approx_eq_rel" Int Int Int Bytes [label(assert_approx_eq_rel)]
 // -----------------------------------------------------------------------------------------------
    rule #assert_eq W1 W2 ERR     => #assert (W1 ==Int W2)  ERR +Bytes String2Bytes(": " +String Int2String(W1) +String " != " +String Int2String(W2))
    rule #assert_ge W1 W2 ERR     => #assert (W1 >=Int W2)  ERR +Bytes String2Bytes(": " +String Int2String(W1) +String " < "  +String Int2String(W2))
    rule #assert_le W1 W2 ERR     => #assert (W1 <=Int W2)  ERR +Bytes String2Bytes(": " +String Int2String(W1) +String " > "  +String Int2String(W2))
    rule #assert_gt W1 W2 ERR     => #assert (W1 >Int W2)   ERR +Bytes String2Bytes(": " +String Int2String(W1) +String " <= " +String Int2String(W2))
    rule #assert_lt W1 W2 ERR     => #assert (W1 <Int W2)   ERR +Bytes String2Bytes(": " +String Int2String(W1) +String " >= " +String Int2String(W2))
    rule #assert_not_eq W1 W2 ERR => #assert (W1 =/=Int W2) ERR +Bytes String2Bytes(": " +String Int2String(W1) +String " == " +String Int2String(W2))
    rule #assert_approx_eq_abs W1 W2 W3 ERR => #assert ((maxInt(W1, W2) -Int minInt(W1, W2)) <=Int W3) ERR 
      +Bytes String2Bytes(": " +String Int2String(W1) +String " !~= " +String Int2String(W2) +String " (max delta: " +String Int2String(W3) +String ", real delta: " +String Int2String(maxInt(W1, W2) -Int minInt(W1, W2)) +String ")")
    rule #assert_approx_eq_rel W1 W2 W3 ERR => #assert (W1 ==Int W2) ERR 
                                        +Bytes String2Bytes(": " +String Int2String(W1) +String " !~= " +String Int2String(W2) 
                                                                 +String " (max delta: " +String Int2String(W3 divInt (10 ^Int 16)) 
                                                                 +String "% , real delta: undefined)")
      requires W2 ==Int 0
    rule #assert_approx_eq_rel W1 W2 W3 ERR => #assert ((((maxInt(W1, W2) -Int minInt(W1, W2)) *Int (10 ^Int 18)) divInt absInt(W2)) <=Int W3) ERR 
                                        +Bytes String2Bytes(": " +String Int2String(W1) +String " !~= " +String Int2String(W2) 
                                                                 +String " (max delta: " +String Int2String(W3 divInt (10 ^Int 16)) +String "% , real delta: " 
                                                                 +String Int2String((((maxInt(W1, W2) -Int minInt(W1, W2)) *Int (10 ^Int 18)) divInt absInt(W2)) divInt (10 ^Int 16)) +String "%)")
      requires W2 =/=Int 0   
```

Capturing cheat code calls
--------------------------

```k
    rule [cheatcode.call.assertEq]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ( "assertEq(address,address)" )
        orBool SELECTOR ==Int selector ( "assertEq(bool,bool)"       )
        orBool SELECTOR ==Int selector ( "assertEq(bytes32,bytes32)" )
        orBool SELECTOR ==Int selector ( "assertEq(int256,int256)"   )
        orBool SELECTOR ==Int selector ( "assertEq(uint256,uint256)" )
    [preserves-definedness]

    rule [cheatcode.call.assertEq.Darray]:
         <k> #cheatcode_call SELECTOR ARGS => 
               #let LEN_INPUT1 = #asWord(#range(ARGS, 0, 32)) #in
               #let OFFSET_INPUT1 = 32 +Int LEN_INPUT1 *Int 32 #in
               #let LEN_INPUT2 = #asWord(#range(ARGS, OFFSET_INPUT1, 32)) #in
                  #assert_eq #asWord(#range(ARGS, 32, LEN_INPUT1 *Int 32)) #asWord(#range(ARGS, 32 +Int OFFSET_INPUT1, LEN_INPUT2 *Int 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ( "assertEq(uint256[],uint256[])" )
        orBool SELECTOR ==Int selector ( "assertEq(int256[],int256[])"   )
        orBool SELECTOR ==Int selector ( "assertEq(bool[],bool[])"       )
        orBool SELECTOR ==Int selector ( "assertEq(bytes32[],bytes32[])" )
        orBool SELECTOR ==Int selector ( "assertEq(address[],address[])" )
    [preserves-definedness]

    rule [cheatcode.call.assertEq.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32))) ... </k>
      requires SELECTOR ==Int selector ( "assertEq(address,address,string)" )
        orBool SELECTOR ==Int selector ( "assertEq(bool,bool,string)"       )
        orBool SELECTOR ==Int selector ( "assertEq(bytes32,bytes32,string)" )
        orBool SELECTOR ==Int selector ( "assertEq(int256,int256,string)"   )
        orBool SELECTOR ==Int selector ( "assertEq(uint256,uint256,string)" )
    [preserves-definedness]

    rule [cheatcode.call.assertNotEq]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_not_eq #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ( "assertNotEq(address,address)" )
        orBool SELECTOR ==Int selector ( "assertNotEq(bool,bool)"       )
        orBool SELECTOR ==Int selector ( "assertNotEq(bytes32,bytes32)" )
        orBool SELECTOR ==Int selector ( "assertNotEq(int256,int256)"   )
        orBool SELECTOR ==Int selector ( "assertNotEq(uint256,uint256)" )
    [preserves-definedness]

    rule [cheatcode.call.assertNotEq.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_not_eq #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32))) ... </k>
      requires SELECTOR ==Int selector ( "assertNotEq(address,address,string)" )
        orBool SELECTOR ==Int selector ( "assertNotEq(bool,bool,string)"       )
        orBool SELECTOR ==Int selector ( "assertNotEq(bytes32,bytes32,string)" )
        orBool SELECTOR ==Int selector ( "assertNotEq(int256,int256,string)"   )
        orBool SELECTOR ==Int selector ( "assertNotEq(uint256,uint256,string)" )
    [preserves-definedness]

    rule [cheatcode.call.assertTrue]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) bool2Word(true) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ( "assertTrue(bool)" )
    [preserves-definedness]

    rule [cheatcode.call.assertTrue.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) bool2Word(true) #range(ARGS, 64, #asWord(#range(ARGS, 32, 32))) ... </k>
      requires SELECTOR ==Int selector ( "assertTrue(bool,string)" )
    [preserves-definedness]

    rule [cheatcode.call.assertFalse]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) bool2Word(false) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ( "assertFalse(bool)" )
    [preserves-definedness]

    rule [cheatcode.call.assertFalse.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_eq #asWord(#range(ARGS, 0, 32)) bool2Word(false) #range(ARGS, 64, #asWord(#range(ARGS, 32, 32))) ... </k>
      requires SELECTOR ==Int selector ( "assertFalse(bool,string)" )
    [preserves-definedness]

    rule [cheatcode.call.assertGe]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_ge #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ("assertGe(uint256,uint256)")
    [preserves-definedness]

    rule [cheatcode.call.assertGe.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_ge #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32))) ... </k>
      requires SELECTOR ==Int selector ("assertGe(uint256,uint256,string)")
    [preserves-definedness]

    rule [cheatcode.call.assertGt]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_gt #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ("assertGt(uint256,uint256)")
    [preserves-definedness]

    rule [cheatcode.call.assertGt.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_gt #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32))) ... </k>
      requires SELECTOR ==Int selector ("assertGt(uint256,uint256,string)")
    [preserves-definedness]

    rule [cheatcode.call.assertLe]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_le #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ("assertLe(uint256,uint256)")
    [preserves-definedness]

    rule [cheatcode.call.assertLe.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_le #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32))) ... </k>
      requires SELECTOR ==Int selector ("assertLe(uint256,uint256,string)")
    [preserves-definedness]

    rule [cheatcode.call.assertLt]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_lt #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ("assertLt(uint256,uint256)")
    [preserves-definedness]

    rule [cheatcode.call.assertLt.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_lt #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32))) ... </k>
      requires SELECTOR ==Int selector ("assertLt(uint256,uint256,string)")
    [preserves-definedness]

    rule [cheatcode.call.assertApproxEqAbs]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_approx_eq_abs #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #asWord(#range(ARGS, 64, 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ( "assertApproxEqAbs(uint256,uint256,uint256)" )
        orBool SELECTOR ==Int selector ( "assertApproxEqAbs(int256,int256,uint256)" )
    [preserves-definedness]

    rule [cheatcode.call.assertApproxEqAbs.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_approx_eq_abs #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #asWord(#range(ARGS, 64, 32)) #range(ARGS, 128, #asWord(#range(ARGS, 96, 32))) ... </k>
      requires SELECTOR ==Int selector ( "assertApproxEqAbs(uint256,uint256,uint256,string)" )
        orBool SELECTOR ==Int selector ( "assertApproxEqAbs(int256,int256,uint256,string)" )
    [preserves-definedness]

    rule [cheatcode.call.assertApproxEqRel]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_approx_eq_rel #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #asWord(#range(ARGS, 64, 32)) String2Bytes("assertion failed") ... </k>
      requires SELECTOR ==Int selector ( "assertApproxEqRel(uint256,uint256,uint256)" )
        orBool SELECTOR ==Int selector ( "assertApproxEqRel(int256,int256,uint256)" )
    [preserves-definedness]

    rule [cheatcode.call.assertApproxEqRel.err]:
         <k> #cheatcode_call SELECTOR ARGS => #assert_approx_eq_rel #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #asWord(#range(ARGS, 64, 32)) #range(ARGS, 128, #asWord(#range(ARGS, 96, 32))) ... </k>
      requires SELECTOR ==Int selector ( "assertApproxEqRel(uint256,uint256,uint256,string)" )
        orBool SELECTOR ==Int selector ( "assertApproxEqRel(int256,int256,uint256,string)" )
    [preserves-definedness]
```

Function selectors
------------------

```k
    rule selector ( "assertEq(address,address)"           ) => 1364419062
    rule selector ( "assertEq(address,address,string)"    ) => 791112145
    rule selector ( "assertEq(bool,bool)"                 ) => 4160631927
    rule selector ( "assertEq(bool,bool,string)"          ) => 1303486078
    rule selector ( "assertEq(bytes32,bytes32)"           ) => 2089076379
    rule selector ( "assertEq(bytes32,bytes32,string)"    ) => 3254394576
    rule selector ( "assertEq(int256,int256)"             ) => 4269076571
    rule selector ( "assertEq(int256,int256,string)"      ) => 1900687123
    rule selector ( "assertEq(uint256,uint256)"           ) => 2552851540
    rule selector ( "assertEq(uint256,uint256,string)"    ) => 2293517445
    rule selector ( "assertEq(uint256[],uint256[])"       ) => 2539477522
    rule selector ( "assertEq(int256[],int256[])"         ) => 1896891308
    rule selector ( "assertEq(bool[],bool[])"             ) => 1887303557
    rule selector ( "assertEq(bytes32[],bytes32[])"       ) => 214560388
    rule selector ( "assertEq(address[],address[])"       ) => 946383924


    rule selector ( "assertTrue(bool)"                    ) => 211801473
    rule selector ( "assertTrue(bool,string)"             ) => 2739854339

    rule selector ("assertFalse(bool)"                    ) => 2778212485
    rule selector ("assertFalse(bool,string)"             ) => 2074101769

    rule selector ( "assertGe(uint256,uint256)"           ) => 2832519641
    rule selector ( "assertGe(uint256,uint256,string)"    ) => 3797041856
    rule selector ( "assertGe(int256,int256)"             ) => 170964849
    rule selector ( "assertGe(int256,int256,string)"      ) => 2822973661

    rule selector ( "assertGt(uint256,uint256)"           ) => 3674733778
    rule selector ( "assertGt(uint256,uint256,string)"    ) => 3651388626
    rule selector ( "assertGt(int256,int256)"             ) => 1513499973
    rule selector ( "assertGt(int256,int256,string)"      ) => 4174592923

    rule selector ( "assertLe(uint256,uint256)"           ) => 2221339669
    rule selector ( "assertLe(uint256,uint256,string)"    ) => 3514649357
    rule selector ( "assertLe(int256,int256)"             ) => 2516391246
    rule selector ( "assertLe(int256,int256,string)"      ) => 1308518700

    rule selector ( "assertLt(uint256,uint256)"           ) => 2972696581
    rule selector ( "assertLt(uint256,uint256,string)"    ) => 1708507445
    rule selector ( "assertLt(int256,int256)"             ) => 1049706624
    rule selector ( "assertLt(int256,int256,string)"      ) => 2683646435

    rule selector ( "assertNotEq(address,address)"        ) => 2972587668
    rule selector ( "assertNotEq(address,address,string)" ) => 2272634257
    rule selector ( "assertNotEq(bool,bool)"              ) => 594431334
    rule selector ( "assertNotEq(bool,bool,string)"       ) => 277979745
    rule selector ( "assertNotEq(bytes32,bytes32)"        ) => 2307818492
    rule selector ( "assertNotEq(bytes32,bytes32,string)" ) => 2989698897
    rule selector ( "assertNotEq(int256,int256)"          ) => 4106224867
    rule selector ( "assertNotEq(int256,int256,string)"   ) => 1193592249
    rule selector ( "assertNotEq(uint256,uint256)"        ) => 3079705376
    rule selector ( "assertNotEq(uint256,uint256,string)" ) => 2566503869

    rule selector ( "assertApproxEqAbs(uint256,uint256,uint256)" )        => 382863302
    rule selector ( "assertApproxEqAbs(uint256,uint256,uint256,string)" ) => 4145066082
    rule selector ( "assertApproxEqAbs(int256,int256,uint256)" )          => 604996509
    rule selector ( "assertApproxEqAbs(int256,int256,uint256,string)" )   => 2190075425

    rule selector ( "assertApproxEqRel(uint256,uint256,uint256)" )        => 2364694260
    rule selector ( "assertApproxEqRel(uint256,uint256,uint256,string)" ) => 516652339
    rule selector ( "assertApproxEqRel(int256,int256,uint256)" )          => 4272083279
    rule selector ( "assertApproxEqRel(int256,int256,uint256,string)" )   => 4012342642
```

```k
endmodule
```