Highly optimized EVM rules
==========================

The provided rules speed up execution and rely on the hypothesis that EVM bytecode
that comes compiled from Solidity will not result in word stack overflows or underflows.

```k
module EVM-RULE-OPTIMIZATIONS
    imports EVM

    rule #stackUnderflow(_, _) => false [priority(30)]
    rule #stackOverflow(_, _) => false [priority(30)]

    rule [super.optimized.pushzero]:
      <k> ( #next[ PUSHZERO ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> WS => 0 : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.push]:
      <k> ( #next[ PUSH(N) ] => .K ) ... </k>
      <useGas> false </useGas>
      <program> PGM </program>
      <wordStack> WS => #asWord( #range(PGM, PCOUNT +Int 1, N) ) : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int N +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.dup]:
      <k> ( #next[ DUP(N) ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> WS => WS [ ( N +Int -1 ) ] : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.swap]:
      <k> ( #next[ SWAP(N) ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : WS => WS [ ( N +Int -1 ) ] : ( WS [ ( N +Int -1 ) := W0 ] ) </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.add]:
      <k> ( #next[ ADD ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => chop ( W0 +Int W1 ) : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.sub]:
      <k> ( #next[ SUB ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => chop ( W0 -Int W1 ) : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.mul]:
      <k> ( #next[ MUL ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => chop ( W0 *Int W1 ) : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.and]:
      <k> ( #next[ AND ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => W0 &Int W1 : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.or]:
      <k> ( #next[ EVMOR ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => W0 |Int W1 : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.xor]:
      <k> ( #next[ XOR ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => W0 xorInt W1 : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.iszero]:
      <k> ( #next[ ISZERO ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : WS => bool2Word ( W0 ==Int 0 ) : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.lt]:
      <k> ( #next[ LT ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => bool2Word ( W0 <Int W1 ) : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.gt]:
      <k> ( #next[ GT ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => bool2Word ( W1 <Int W0 ) : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

    rule [super.optimized.eq]:
      <k> ( #next[ EQ ] => .K ) ... </k>
      <useGas> false </useGas>
      <wordStack> W0 : W1 : WS => bool2Word ( W0 ==Int W1 ) : WS </wordStack>
      <pc> PCOUNT => PCOUNT +Int 1 </pc>
      [priority(30)]

endmodule
```