requires "../contracts.k"

module SUM-TO-N-INVARIANT

  imports S2KtestZModLoopsTest-CONTRACT

  rule N xorInt maxUInt256 => maxUInt256 -Int N 
  requires #rangeUInt(256, N)
  [simplification]

  rule [foundry-sum-to-n-loop-invariant]:
  <kevm>
    <k>
      ((JUMPI 2423 CONDITION) => JUMP 2423)
      ~> #pc [ JUMPI ]
      ~> #execute
      ...
    </k>
    <mode>
      NORMAL
    </mode>
    <schedule>
      SHANGHAI
    </schedule>
    <ethereum>
      <evm>
        <callState>
          <program>
            PROGRAM
          </program>
          <jumpDests>
            JUMPDESTS
          </jumpDests>
          <wordStack>
              (S => (S +Int ((N *Int (N +Int 1)) /Int 2)))
            : 0 
            : (N => 0)
            : 459 
            : 2123244496 
            : .WordStack
          </wordStack>
          <pc>
            2393
          </pc>
          <gas>
            GAS_AMT:Int => GAS_AMT -Int (N *Int 178)
          </gas>
          ...
        </callState>
        ...
      </evm>
      ...
    </ethereum>
    ...
  </kevm>

  requires 0 <Int N
   andBool #rangeUInt(256, S +Int ((N *Int (N +Int 1)) /Int 2))
   andBool #rangeUInt(256, N)
   andBool #rangeUInt(256, S)
   andBool GAS_AMT >=Int N *Int 178
   andBool CONDITION ==K bool2Word ( N:Int ==Int 0 )
   andBool PROGRAM ==K #binRuntime(S2KtestZModLoopsTest)
   andBool JUMPDESTS ==K #computeValidJumpDests(#binRuntime(S2KtestZModLoopsTest))
  [priority(40)]

endmodule


module SYMBOLIC-BYTES-LEMMAS

  imports S2KtestZModFreshIntTest-CONTRACT

    // Deconstruction of (notMaxUInt &Int ...)
    rule notMaxUInt8   &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 31) +Bytes #buf (  1, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt16  &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 30) +Bytes #buf (  2, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt32  &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 28) +Bytes #buf (  4, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt64  &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 24) +Bytes #buf (  8, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt96  &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 20) +Bytes #buf ( 12, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt128 &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 16) +Bytes #buf ( 16, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt160 &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 12) +Bytes #buf ( 20, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt192 &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 8)  +Bytes #buf ( 24, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt208 &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 6)  +Bytes #buf ( 26, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt224 &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 4)  +Bytes #buf ( 28, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt240 &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 2)  +Bytes #buf ( 30, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule notMaxUInt248 &Int #asWord ( BA ) => #asWord ( #range(BA, 0, 1)  +Bytes #buf ( 31, 0 ) ) requires lengthBytes(BA) ==Int 32 [simplification]


    rule ( notMaxUInt5 &Int ( ( notMaxUInt5 &Int X ) +Int Y ) ) => ( notMaxUInt5 &Int X ) +Int ( notMaxUInt5 &Int Y )
      requires #rangeUInt(256, X) andBool #rangeUInt(256, Y)
      [simplification, concrete(Y)]


endmodule
