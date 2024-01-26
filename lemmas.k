requires "../contracts.k"

module TEST-LEMMAS

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
