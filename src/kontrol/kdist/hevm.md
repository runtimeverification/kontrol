### hevm Success Predicate

The [hevm](https://github.com/ethereum/hevm) success predicate option was implemented for [benchmarking](https://github.com/eth-sc-comp/benchmarks/tree/deb3faa7e42993a057ba52935368a89f08970f19) purposes.

`hevm symbolic` searches for assertions violations, where an assertion violation is defined as either an execution of the invalid opcode (`0xfe`), or a revert with a message of the form `abi.encodeWithSelector('Panic(uint256)', errCode)` with `errCode` being one of the predefined Solidity assertion codes defined [here](https://docs.soliditylang.org/en/latest/control-structures.html#panic-via-assert-and-error-via-require) (by default, `hevm` ignores assertion violations that result from arithmetic overflow (`Panic(0x11)`).

Notice that `hevm symbolic` does not fail with `revert` statements, nor with `require` clauses. Instead `require` clauses are used to impose assumptions, being the equivalent to `vm.assume`.

Although `hevm symbolic` does not fail on `DSTest` assertions, for compatibility with `hevm test` and `Halmos`, we decided to check only user-defined solidity assertion violations and `DSTest` violations, in addition to the invalid opcode.

```k
module HEVM-SUCCESS
    imports EVM
    imports EVM-ABI

  syntax Bool ::=
      "hevm_success" "("
        statusCode: StatusCode ","
        failed: Int ","
        output: Bytes
      ")" [function, klabel(hevm_success), symbol]
 // ----------------------------------------------
    rule hevm_success(EVMC_SUCCESS, 0, _)  => true
    rule hevm_success(EVMC_REVERT, _, OUT) => true
      requires notBool( #range(OUT, 0, 4)  ==K Int2Bytes(4, selector ("Panic(uint256)"), BE)
                andBool #range(OUT, 35, 1) ==K b"\x01" ) //Error code for user defined assertions
    rule hevm_success(_, _, _)             => false [owise]

    rule ( selector ( "Panic(uint256)" ) => 1313373041 )
```

### hevm Fail Predicate

In order to support `proveFail` we also defined the hevm fail predicate. This predicate asserts that all branches are failing, i.e. there is not a branch ending with `EVMC_SUCCESS` and not violating a `DS-TEST` assertion.

`proveFail` is not supported by `hevm symbolic`, however it is supported by `hevm test`. Therefore, this predicate is defined to be compatible with `hevm test`, meaning that it checks whether all branches revert. 

```k
    syntax Bool ::=
      "hevm_fail" "("
        statusCode: StatusCode ","
        failed: Int
      ")" [function, klabel(hevm_fail), symbol]
 // -------------------------------------------
    rule hevm_fail(EVMC_SUCCESS, 0) => false
    rule hevm_fail(_, _)            => true [owise]

endmodule
```
