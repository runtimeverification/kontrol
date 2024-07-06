requires "evm.md"
requires "foundry.md"

module SYMBOLIC-BYTES-LEMMAS
    imports BOOL
    imports FOUNDRY
    imports INFINITE-GAS
    imports INT-SYMBOLIC

    //
    // Byte indexing in terms of #asWord
    //
    rule BA [ X ] => #asWord ( #range (BA, X, 1) )
      requires X <=Int lengthBytes(BA)
      [simplification(40)]

    rule [bytes-concat-lookup-left]:
        (A:Bytes +Bytes _:Bytes) [I] => A [I]
      requires 0 <=Int I andBool I <Int lengthBytes(A)
      [simplification, preserves-definedness]

    rule [bytes-concat-lookup-right]:
        (A:Bytes +Bytes B:Bytes) [I] => B [I -Int lengthBytes(A)]
      requires lengthBytes(A) <=Int I
      [simplification, preserves-definedness]

    //
    // Equality of +Bytes
    //
    rule { B:Bytes #Equals B1:Bytes +Bytes B2:Bytes } =>
           { #range ( B, 0, lengthBytes(B1) ) #Equals B1 } #And
           { #range ( B, lengthBytes(B1), lengthBytes(B) -Int lengthBytes(B1) ) #Equals B2 }
      requires lengthBytes(B1) <=Int lengthBytes(B)
      [simplification(60), concrete(B)]

    rule { B1:Bytes +Bytes B2:Bytes #Equals B } =>
           { #range ( B, 0, lengthBytes(B1) ) #Equals B1 } #And
           { #range ( B, lengthBytes(B1), lengthBytes(B) -Int lengthBytes(B1) ) #Equals B2 }
      requires lengthBytes(B1) <=Int lengthBytes(B)
      [simplification(60), concrete(B)]

    rule { B:Bytes #Equals #buf( N, X:Int ) +Bytes B2:Bytes } =>
           { X #Equals #asWord ( #range ( B, 0, N ) ) } #And
           { #range ( B, N, lengthBytes(B) -Int N ) #Equals B2 }
      requires N <=Int lengthBytes(B)
      [simplification(60), concrete(B, N), preserves-definedness]

    rule { #buf( N, X:Int ) +Bytes B2:Bytes #Equals B } =>
           { X #Equals #asWord ( #range ( B, 0, N ) ) } #And
           { #range ( B, N, lengthBytes(B) -Int N ) #Equals B2 }
      requires N <=Int lengthBytes(B)
      [simplification(60), concrete(B, N), preserves-definedness]

    rule { B #Equals #buf( N, X:Int ) } => { #asInteger ( B ) #Equals X modInt (2 ^Int (8 *Int N)) }
      requires lengthBytes(B) ==Int N
      [simplification(80), concrete(B)]

    //
    // Equality of #asWord
    //
    rule { X:Int #Equals #asWord ( B:Bytes ) } => { #buf ( 32, X ) #Equals B }
      requires #rangeUInt(256, X) andBool lengthBytes( B ) ==Int 32
      [simplification, concrete(X), preserves-definedness]

    //
    // String-related manipulation
    //
    rule [bitwise-and-to-right]:
      X:Int &Int #asWord ( B1:Bytes +Bytes B2:Bytes ) => X &Int #asWord ( B2 )
      requires #rangeUInt(256, X)
       andBool lengthBytes(B1:Bytes +Bytes B2) <=Int 32
       andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
       andBool log2Int(X +Int 1) <=Int lengthBytes(B2) *Int 8
       [simplification, concrete(X), preserves-definedness]

    rule [bitwise-and-shift]:
      X:Int &Int ( #asWord ( B1:Bytes +Bytes B2:Bytes ) >>Int Y:Int ) => X &Int ( #asWord ( B2 ) >>Int Y )
      requires #rangeUInt(256, X)
       andBool 0 <=Int Y andBool Y <Int 256
       andBool lengthBytes(B1:Bytes +Bytes B2) <=Int 32
       andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
       andBool log2Int(X +Int 1) <=Int ( lengthBytes(B2) *Int 8 -Int Y )
       [simplification, concrete(X, Y), preserves-definedness]

    rule [string-is-short]:
      1 &Int ( 2 *Int X:Int ) => 0
      requires 0 <=Int X
      [simplification]

    //
    // Arithmetic
    //
    rule ( A:Int *Int B:Int ) >>Int C:Int => ( A /Int ( 2 ^Int C ) ) *Int B
      requires 0 <=Int A andBool 0 <=Int B andBool 0 <=Int C
       andBool A modInt ( 2 ^Int C ) ==Int 0
      [simplification, concrete(A, C)]

endmodule