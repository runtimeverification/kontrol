requires "evm.md"
requires "foundry.md"

module SYMBOLIC-BYTES-LEMMAS
    imports BOOL
    imports FOUNDRY
    imports INFINITE-GAS
    imports INT-SYMBOLIC

    // Byte indexing in terms of #asWord
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

    rule { B:Bytes #Equals B1:Bytes +Bytes B2:Bytes } =>
           { #range ( B, 0, lengthBytes(B1) ) #Equals B1 } #And
           { #range ( B, lengthBytes(B1), lengthBytes(B) -Int lengthBytes(B1) ) #Equals B2 }
      requires lengthBytes(B1) <=Int lengthBytes(B)
      [simplification(60), concrete(B, B1)]

    rule { B1:Bytes +Bytes B2:Bytes #Equals B } =>
           { #range ( B, 0, lengthBytes(B1) ) #Equals B1 } #And
           { #range ( B, lengthBytes(B1), lengthBytes(B) -Int lengthBytes(B1) ) #Equals B2 }
      requires lengthBytes(B1) <=Int lengthBytes(B)
      [simplification(60), concrete(B, B1)]

    rule { B:Bytes #Equals #buf( N, X:Int ) +Bytes B2:Bytes } =>
           { X #Equals #asWord ( #range ( B, 0, N ) ) } #And
           { #range ( B, N, lengthBytes(B) -Int N ) #Equals B2 }
      requires N <=Int lengthBytes(B)
      [simplification(60), concrete(B, N)]

    rule { #buf( N, X:Int ) +Bytes B2:Bytes #Equals B } =>
           { X #Equals #asWord ( #range ( B, 0, N ) ) } #And
           { #range ( B, N, lengthBytes(B) -Int N ) #Equals B2 }
      requires N <=Int lengthBytes(B)
      [simplification(60), concrete(B, N)]

endmodule