#[Kontrol documentation](https://docs.runtimeverification.com/kontrol).

The documentation below may become deprecated. The documentation at the link above will be continuously updated and improved.

Foundry Module for Kontrol
--------------------------

Foundry's testing framework provides a series of cheatcodes so that developers can specify what situation they want to test.
This file describes the K semantics of the Foundry testing framework, which includes the definition of said cheatcodes and what does it mean for a test to pass.

```k
requires "cheatcodes.md"
requires "hevm.md"
requires "hashed-locations.md"
requires "edsl.md"
requires "trace.md"
requires "assert.md"
requires "lemmas/lemmas.k"

module FOUNDRY
    imports FOUNDRY-SUCCESS
    imports FOUNDRY-CHEAT-CODES
    imports FOUNDRY-ACCOUNTS
    imports HEVM-SUCCESS
    imports EVM-TRACING
    imports KONTROL-ASSERTIONS
    imports EDSL
    imports LEMMAS

    configuration
      <foundry>
        <kevm/>
        <cheatcodes/>
        <KEVMTracing/>
      </foundry>
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
```

Then, we define helpers in K which can:

-   Inject a given boolean condition into's this execution's path condition
-   Set the `FoundryCheat . Failed` location to `True`.

```k
    syntax KItem ::= #assume ( Bool ) [klabel(cheatcode_assume), symbol]
 // --------------------------------------------------------------------
    rule <k> #assume(B) => .K ... </k> ensures B

     syntax KItem ::= "#markAsFailed" [klabel(foundry_markAsFailed)]
  // ---------------------------------------------------------------
     rule <k> #markAsFailed => .K ... </k>
          <account>
             <acctID> #address(FoundryCheat) </acctID>
             <storage> STORAGE => STORAGE [ #loc(FoundryCheat . Failed) <- 1 ] </storage>
             ...
           </account>
```

#### Structure of execution

The `cheatcode.call` rule is used to inject specific behaviour for each cheat code.
The rule has a higher priority than any other `#call` rule and will match every call made to the [FoundryCheat address](https://book.getfoundry.sh/cheatcodes/#cheatcodes-reference).
The function selector, represented as `#asWord(#range(ARGS, 0, 4))` and the call data `#range(ARGS, 4, lengthBytes(ARGS) -Int 4)` are passed to the `#cheatcode_call` production, which will further rewrite using rules defined for implemented cheat codes.
Finally, the rule for `#cheatcode_return` is used to end the execution of the `CALL` OpCode.

```k
    rule [cheatcode.call]:
         <k> (#checkCall _ _
          ~> #call _ CHEAT_ADDR _ _ _ ARGS _
          ~> #return RETSTART RETWIDTH )
          => #cheatcode_call #asWord(#range(ARGS, 0, 4)) #range(ARGS, 4, lengthBytes(ARGS) -Int 4)
          ~> #cheatcode_return RETSTART RETWIDTH
         ...
         </k>
         <output> _ => .Bytes </output>
    requires CHEAT_ADDR ==Int #address(FoundryCheat)
    [priority(40)]
```

We define two productions named `#cheatcode_return` and `#cheatcode_call`, which will be used by each cheat code.
The rule `cheatcode.return` will rewrite the `#cheatcode_return` production into other productions that will place the output of the execution into the local memory, refund the gas value of the call and push the value `1` on the call stack.

```k
    syntax KItem ::= "#cheatcode_return" Int Int  [klabel(cheatcode_return)]
                   | "#cheatcode_call" Int Bytes  [klabel(cheatcode_call)  ]
                   | "#cheatcode_error" Int Bytes [klabel(cheatcode_error) ]
 // ------------------------------------------------------------------------
    rule [cheatcode.return]:
         <k> #cheatcode_return RETSTART RETWIDTH
          => #setLocalMem RETSTART RETWIDTH OUT
          ~> #refund GCALL
          ~> 1 ~> #push
          ... </k>
         <output> OUT </output>
         <callGas> GCALL </callGas>
```

We define a new status code:
 - `CHEATCODE_UNIMPLEMENTED`, which signals that the execution ran into an unimplemented cheat code.

```k
    syntax ExceptionalStatusCode ::= "CHEATCODE_UNIMPLEMENTED"
 // ---------------------------------------------------------
```

```k
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
