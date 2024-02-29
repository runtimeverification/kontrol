The hevm success predicate option was implemented for [benchmarking](https://github.com/eth-sc-comp/benchmarks/tree/deb3faa7e42993a057ba52935368a89f08970f19) purposes.

The `hevm symbolic` searches for assertions violations, where an assertion violation is defined as either an execution of the invalid opcode (`0xfe`), or a revert with a message of the form `abi.encodeWithSelector('Panic(uint256)', errCode)` with `errCode` being one of the predefined solc assertion codes defined [here](https://docs.soliditylang.org/en/latest/control-structures.html#panic-via-assert-and-error-via-require) (by default, hevm ignores assertion violations that result from arithmetic overflow (`Panic(0x11)`).

Although `hevm symbolic` does not fail on `DSTest` assertions, since this implementation is for benchmarking purposes, we decided to check only user-defined solidity assertion violations and `DSTest` violations, in addition to the invalid opcode.

```k
module HEVM-SUCCESS
    imports EVM

  syntax Bool ::=
      "hevm_success" "("
        statusCode: StatusCode ","
        failed: Int ","
        output: Bytes
      ")" [function, klabel(hevm_success), symbol]
 // ----------------------------------------------
    rule hevm_success(EVMC_INVALID_INSTRUCTION, _, _) => false
    rule hevm_success(EVMC_REVERT, _, OUT)            => false
      requires #range(OUT, 0, 4)  ==K Int2Bytes(4, 1313373041, BE) // b"\x4e\x48\x7b\x71"
       andBool #range(OUT, 35, 1) ==K b"\x01"
    rule hevm_success(_, DST , _)                     => false requires DST =/=Int 0
    rule hevm_success(_, _, _)                        => true [owise]

    // rule ( selector ( "Panic(uint256)" ) => 1313373041 )

endmodule
```
