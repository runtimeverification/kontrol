#[Kontrol documentation](https://docs.runtimeverification.com/kontrol).

The documentation below may become deprecated. The documentation at the link above will be continuously updated and improved.

Foundry Module for Kontrol
--------------------------

Foundry's testing framework provides a series of cheatcodes so that developers can specify what situation they want to test.
This file describes the K semantics of the Foundry testing framework, which includes the definition of said cheatcodes and what does it mean for a test to pass.

```k
requires "cheatcodes.md"
requires "hashed-locations.md"
requires "edsl.md"
requires "lemmas/lemmas.k"

module FOUNDRY
    imports FOUNDRY-SUCCESS
    imports FOUNDRY-CHEAT-CODES
    imports FOUNDRY-ACCOUNTS
    imports EDSL
    imports LEMMAS

    configuration
      <foundry>
        <kevm/>
        <cheatcodes/>
        <noGas> false </noGas>
      </foundry>
```

### Disable gas computations in KEVM rules

Override functions that must not be called in no-gas mode.
This will ensure that the execution gets stuck if these are called.
The indenting indicates dependence (e.g., `#memory[_, _]` is only called from `#gas[_, _]`)

```k
    syntax KItem ::= "NOT_PERMITTED" String

    rule       <noGas> true </noGas> <k>      #gas               [ _, _ ] => NOT_PERMITTED "#gas [ _, _ ]"       ... </k> [priority(40)]
      rule     <noGas> true </noGas> <k>      #memory            [ _, _ ] => NOT_PERMITTED "#memory [ _, _ ]"    ... </k> [priority(40)]
        rule   <noGas> true </noGas> <k> _ ~> #deductMemory               => NOT_PERMITTED "#deductMemory"       ... </k> [priority(40)]
          rule <noGas> true </noGas> <k> _ ~> #deductMemoryGas            => NOT_PERMITTED "#deductMemoryGas"    ... </k> [priority(40)]
      rule     <noGas> true </noGas> <k>      #access            [ _, _ ] => NOT_PERMITTED "#access [ _, _ ]"    ... </k> [priority(40)]
        rule   <noGas> true </noGas> <k>      #gasAccess         ( _, _ ) => NOT_PERMITTED "#gasAccess ( _, _ )" ... </k> [priority(40)]
      rule     <noGas> true </noGas> <k>      #gas               [    _ ] => NOT_PERMITTED "#gas [ _ ]"          ... </k> [priority(40)]
        rule   <noGas> true </noGas> <k>      #gasExec           ( _, _ ) => NOT_PERMITTED "#gasExec ( _, _ )"   ... </k> [priority(40)]
          rule <noGas> true </noGas> <k> _ ~> #allocateCallGas            => NOT_PERMITTED "#allocateCallGas"    ... </k> [priority(40)]
          rule <noGas> true </noGas> <k>      #allocateCreateGas          => NOT_PERMITTED "#allocateCreateGas"  ... </k> [priority(40)]

    rule <noGas> true </noGas> <k>      #refund    _ => NOT_PERMITTED "#refund _"  ... </k> [priority(40)]
    rule <noGas> true </noGas> <k> _ ~> #deductGas   => NOT_PERMITTED "#deductGas" ... </k> [priority(40)]
```

Overwrite KEVM rules to skip gas computations when the `<noGas>` cell is set to `true`.

Adapt rules to not use `#gas [ _, _ ]` and, by extension, its underlying auxiliary functions.

```k
    rule <noGas> true </noGas> <k> #exec [ OP              ] => OP              ... </k> requires isNullStackOp(OP) orBool isPushOp(OP) [priority(40)]

    rule <noGas> true </noGas> <k> #exec [ UOP:UnStackOp   ] => UOP W0          ... </k> <wordStack> W0 : WS                => WS </wordStack> [priority(40)]
    rule <noGas> true </noGas> <k> #exec [ BOP:BinStackOp  ] => BOP W0 W1       ... </k> <wordStack> W0 : W1 : WS           => WS </wordStack> [priority(40)]
    rule <noGas> true </noGas> <k> #exec [ TOP:TernStackOp ] => TOP W0 W1 W2    ... </k> <wordStack> W0 : W1 : W2 : WS      => WS </wordStack> [priority(40)]
    rule <noGas> true </noGas> <k> #exec [ QOP:QuadStackOp ] => QOP W0 W1 W2 W3 ... </k> <wordStack> W0 : W1 : W2 : W3 : WS => WS </wordStack> [priority(40)]
    rule <noGas> true </noGas> <k> #exec [ SO:StackOp      ] => SO WS           ... </k> <wordStack> WS </wordStack>                           [priority(40)]

    rule <noGas> true </noGas> <k> #exec [ CSO:CallSixOp   ] => CSO W0 W1 W2 W3 W4 W5    ... </k> <wordStack> W0 : W1 : W2 : W3 : W4 : W5 :      WS => WS </wordStack> [priority(40)]
    rule <noGas> true </noGas> <k> #exec [ CO:CallOp       ] => CO  W0 W1 W2 W3 W4 W5 W6 ... </k> <wordStack> W0 : W1 : W2 : W3 : W4 : W5 : W6 : WS => WS </wordStack> [priority(40)]
```

Adapt rules to not use `#refund _`.

```k
    rule <k> #checkCall ACCT VALUE
          => #pushCallStack ~> #pushWorldState
          ~> #end #if VALUE >Int BAL #then EVMC_BALANCE_UNDERFLOW #else #if CD >=Int 1024 #then EVMC_CALL_DEPTH_EXCEEDED #else EVMC_NONCE_EXCEEDED #fi #fi
         ...
         </k>
         <noGas> true </noGas>
         <callDepth> CD </callDepth>
         <output> _ => .Bytes </output>
         <account>
           <acctID> ACCT </acctID>
           <balance> BAL </balance>
           <nonce> NONCE </nonce>
           ...
         </account>
      requires VALUE >Int BAL orBool CD >=Int 1024 orBool notBool #rangeNonce(NONCE)
      [priority(45)]

    rule [return.revert.noGas]:
         <statusCode> EVMC_REVERT </statusCode>
         <k> #halt ~> #return RETSTART RETWIDTH
          => #popCallStack ~> #popWorldState
          ~> 0 ~> #push ~> #setLocalMem RETSTART RETWIDTH OUT
         ...
         </k>
         <noGas> true </noGas>
         <output> OUT </output>
      [priority(40)]

    rule [return.success.noGas]:
         <statusCode> EVMC_SUCCESS </statusCode>
         <k> #halt ~> #return RETSTART RETWIDTH
          => #popCallStack ~> #dropWorldState
          ~> 1 ~> #push ~> #setLocalMem RETSTART RETWIDTH OUT
         ...
         </k>
         <noGas> true </noGas>
         <output> OUT </output>
      [priority(40)]

    rule <statusCode> EVMC_REVERT </statusCode>
         <noGas> true </noGas>
         <k> #halt ~> #codeDeposit _ => #popCallStack ~> #popWorldState ~> 0 ~> #push ... </k>
      [priority(40)]

    rule <k> #finishCodeDeposit ACCT OUT
          => #popCallStack ~> #dropWorldState ~> ACCT ~> #push
         ...
         </k>
         <noGas> true </noGas>
         <account>
           <acctID> ACCT </acctID>
           <code> _ => OUT </code>
           ...
         </account>
      [priority(40)]

    rule <statusCode> _:ExceptionalStatusCode </statusCode>
         <k> #halt ~> #finishCodeDeposit ACCT _
          => #popCallStack ~> #dropWorldState ~> ACCT ~> #push
         ...
         </k>
         <noGas> true </noGas>
         <schedule> FRONTIER </schedule>
      [priority(40)]
```

Adapt rules to not use `#deductGas`.

```k
    rule <k> #mkCodeDeposit ACCT => #finishCodeDeposit ACCT OUT ... </k>
         <noGas> true </noGas>
         <schedule> SCHED </schedule>
         <output> OUT => .Bytes </output>
      requires lengthBytes(OUT) <=Int maxCodeSize < SCHED > andBool #isValidCode(OUT, SCHED)
      [priority(40)]
```

Adapt other rules that use the `<gas>` cell.

```k
    // Also used `<gasUsed>`, `<gasPrice>`, `<refund>`, `<balance>`, and `<txGasLimit>`
    rule <k> #finalizeTx(false => true) ... </k>
         <noGas> true </noGas>
         <txPending> ListItem(_:Int) REST => REST </txPending>
      [priority(40)]

    // Also used `<callGas>`
    rule <k> #mkCall ACCTFROM ACCTTO ACCTCODE BYTES APPVALUE ARGS STATIC:Bool
          => #touchAccounts ACCTFROM ACCTTO ~> #accessAccounts ACCTFROM ACCTTO ~> #loadProgram BYTES ~> #initVM ~> #precompiled?(ACCTCODE, SCHED) ~> #execute
         ...
         </k>
         <noGas> true </noGas>
         <callDepth> CD => CD +Int 1 </callDepth>
         <callData> _ => ARGS </callData>
         <callValue> _ => APPVALUE </callValue>
         <id> _ => ACCTTO </id>
         <caller> _ => ACCTFROM </caller>
         <static> OLDSTATIC:Bool => OLDSTATIC orBool STATIC </static>
         <schedule> SCHED </schedule>
      [priority(40)]

    // Also used `<callGas>`
    rule <k> #mkCreate ACCTFROM ACCTTO VALUE INITCODE
          => #touchAccounts ACCTFROM ACCTTO ~> #accessAccounts ACCTFROM ACCTTO ~> #loadProgram INITCODE ~> #initVM ~> #execute
         ...
         </k>
         <noGas> true </noGas>
         <id> _ => ACCTTO </id>
         <caller> _ => ACCTFROM </caller>
         <callDepth> CD => CD +Int 1 </callDepth>
         <callData> _ => .Bytes </callData>
         <callValue> _ => VALUE </callValue>
         <account>
           <acctID> ACCTTO </acctID>
           <nonce> NONCE => NONCE +Int 1 </nonce>
           ...
         </account>
      [priority(40)]
```

Adapt cheatcode logic.

```k
    rule [foundry.call.infiniteGas.noGas]:
         <k> #call_foundry SELECTOR _ARGS => NOT_PERMITTED "infiniteGas()" ... </k>
         <noGas> true </noGas>
      requires SELECTOR ==Int selector ( "infiniteGas()" )
      [priority(40)]

    rule [foundry.call.setGas.noGas]:
         <k> #call_foundry SELECTOR _ARGS => NOT_PERMITTED "setGas(uint256)" ... </k>
         <noGas> true </noGas>
      requires SELECTOR ==Int selector ( "setGas(uint256)" )
      [priority(40)]

    rule [foundry.return.noGas]:
         <k> #return_foundry RETSTART RETWIDTH
          => #setLocalMem RETSTART RETWIDTH OUT
          ~> 1 ~> #push
          ... </k>
         <output> OUT </output>
         <noGas> true </noGas>
      [priority(40)]
```

```k
endmodule
```

### Foundry Success Predicate

Foundry has several baked-in convenience accounts for helping to define the "cheat-codes".
Here we define their addresses, and important storage-locations.

```k
module FOUNDRY-ACCOUNTS
    imports SOLIDITY-FIELDS

    syntax Int             ::= #address ( Contract ) [macro]
    syntax Contract        ::= FoundryContract
    syntax Field           ::= FoundryField
    syntax FoundryContract ::= "FoundryTest"  [klabel(contract_FoundryTest)]
                             | "FoundryCheat" [klabel(contract_FoundryCheat)]
 // -------------------------------------------------------------------------
    rule #address(FoundryTest)  => 728815563385977040452943777879061427756277306518  // 0x7FA9385bE102ac3EAc297483Dd6233D62b3e1496
    rule #address(FoundryCheat) => 645326474426547203313410069153905908525362434349  // 0x7109709ECfa91a80626fF3989D68f67F5b1DD12D

    syntax FoundryField ::= "Failed" [klabel(slot_failed)]
 // ------------------------------------------------------
    rule #loc(FoundryCheat . Failed) => 46308022326495007027972728677917914892729792999299745830475596687180801507328 // 0x6661696c65640000000000000000000000000000000000000000000000000000

endmodule
```

The Foundry success predicate performs the same checks as [the `is_success` function from Foundry in `evm/src/executor/mod.rs`](https://github.com/foundry-rs/foundry/blob/e530c7325816e4256f62f4426bd9985dc54da831/evm/src/executor/mod.rs#L490).

These checks are:

-   The call to the test contract has not reverted, and
-   `DSTest.assert*` have not failed.

The last condition is implemented in the [`fail()` function from `DSTest`](https://github.com/dapphub/ds-test/blob/9310e879db8ba3ea6d5c6489a579118fd264a3f5/src/test.sol#L65).
If a DSTest assertion should fail, the `fail()` function stores `bytes32(uint256(0x01))` at the storage slot `bytes32("failed")`.
Hence, checking if a `DSTest.assert*` has failed amounts to reading as a boolean the data from that particular storage slot.

**TODO**: It should also be checked if the code present in the `FoundryCheat` account is non-empty, and return false if it is.

```k
module FOUNDRY-SUCCESS
    imports EVM

    syntax Bool ::=
      "foundry_success" "("
        statusCode: StatusCode ","
        failed: Int ","
        revertExpected: Bool ","
        opcodeExpected: Bool ","
        recordEventExpected: Bool ","
        eventExpected: Bool
      ")" [function, klabel(foundry_success), symbol]
 // -------------------------------------------------
    rule foundry_success(EVMC_SUCCESS, 0, false, false, false, false) => true
    rule foundry_success(_, _, _, _, _, _)                            => false [owise]

endmodule
```
