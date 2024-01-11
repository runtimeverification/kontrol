requires "../contracts.k"

module TEST-LEMMAS

  imports S2KtestZModFreshIntTest-CONTRACT

    // Deconstruction of (maxUInt &Int ...)
    rule maxUInt8   &Int #asWord ( BA ) => #asWord ( #range(BA, 31,  1) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt16  &Int #asWord ( BA ) => #asWord ( #range(BA, 30,  2) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt24  &Int #asWord ( BA ) => #asWord ( #range(BA, 29,  3) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt32  &Int #asWord ( BA ) => #asWord ( #range(BA, 28,  4) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt40  &Int #asWord ( BA ) => #asWord ( #range(BA, 27,  5) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt48  &Int #asWord ( BA ) => #asWord ( #range(BA, 26,  6) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt56  &Int #asWord ( BA ) => #asWord ( #range(BA, 25,  7) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt64  &Int #asWord ( BA ) => #asWord ( #range(BA, 24,  8) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt72  &Int #asWord ( BA ) => #asWord ( #range(BA, 23,  9) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt80  &Int #asWord ( BA ) => #asWord ( #range(BA, 22, 10) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt88  &Int #asWord ( BA ) => #asWord ( #range(BA, 21, 11) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt96  &Int #asWord ( BA ) => #asWord ( #range(BA, 20, 12) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt104 &Int #asWord ( BA ) => #asWord ( #range(BA, 19, 13) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt112 &Int #asWord ( BA ) => #asWord ( #range(BA, 18, 14) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt120 &Int #asWord ( BA ) => #asWord ( #range(BA, 17, 15) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt128 &Int #asWord ( BA ) => #asWord ( #range(BA, 16, 16) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt136 &Int #asWord ( BA ) => #asWord ( #range(BA, 15, 17) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt144 &Int #asWord ( BA ) => #asWord ( #range(BA, 14, 18) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt152 &Int #asWord ( BA ) => #asWord ( #range(BA, 13, 19) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt160 &Int #asWord ( BA ) => #asWord ( #range(BA, 12, 20) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt168 &Int #asWord ( BA ) => #asWord ( #range(BA, 11, 21) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt176 &Int #asWord ( BA ) => #asWord ( #range(BA, 10, 22) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt184 &Int #asWord ( BA ) => #asWord ( #range(BA,  9, 23) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt192 &Int #asWord ( BA ) => #asWord ( #range(BA,  8, 24) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt200 &Int #asWord ( BA ) => #asWord ( #range(BA,  7, 25) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt208 &Int #asWord ( BA ) => #asWord ( #range(BA,  6, 26) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt216 &Int #asWord ( BA ) => #asWord ( #range(BA,  5, 27) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt224 &Int #asWord ( BA ) => #asWord ( #range(BA,  4, 28) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt232 &Int #asWord ( BA ) => #asWord ( #range(BA,  3, 29) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt240 &Int #asWord ( BA ) => #asWord ( #range(BA,  2, 30) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt248 &Int #asWord ( BA ) => #asWord ( #range(BA,  1, 31) ) requires lengthBytes(BA) ==Int 32 [simplification]
    rule maxUInt256 &Int #asWord ( BA ) => #asWord ( #range(BA,  0, 32) ) requires lengthBytes(BA) ==Int 32 [simplification]

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

    // Irrelevance of lower bits
    rule notMaxUInt8   &Int (X |Int (maxUInt8   &Int _)) => notMaxUInt8   &Int X [simplification]
    rule notMaxUInt16  &Int (X |Int (maxUInt16  &Int _)) => notMaxUInt16  &Int X [simplification]
    rule notMaxUInt32  &Int (X |Int (maxUInt32  &Int _)) => notMaxUInt32  &Int X [simplification]
    rule notMaxUInt64  &Int (X |Int (maxUInt64  &Int _)) => notMaxUInt64  &Int X [simplification]
    rule notMaxUInt96  &Int (X |Int (maxUInt96  &Int _)) => notMaxUInt96  &Int X [simplification]
    rule notMaxUInt128 &Int (X |Int (maxUInt128 &Int _)) => notMaxUInt128 &Int X [simplification]
    rule notMaxUInt160 &Int (X |Int (maxUInt160 &Int _)) => notMaxUInt160 &Int X [simplification]
    rule notMaxUInt192 &Int (X |Int (maxUInt192 &Int _)) => notMaxUInt192 &Int X [simplification]
    rule notMaxUInt208 &Int (X |Int (maxUInt208 &Int _)) => notMaxUInt208 &Int X [simplification]
    rule notMaxUInt224 &Int (X |Int (maxUInt224 &Int _)) => notMaxUInt224 &Int X [simplification]
    rule notMaxUInt240 &Int (X |Int (maxUInt240 &Int _)) => notMaxUInt240 &Int X [simplification]
    rule notMaxUInt248 &Int (X |Int (maxUInt248 &Int _)) => notMaxUInt248 &Int X [simplification]

endmodule
