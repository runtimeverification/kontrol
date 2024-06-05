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
        (A:Bytes +Bytes B:Bytes) [I] => A [I]
      requires 0 <=Int I andBool I <Int lengthBytes(A)
      [simplification, preserves-definedness]

    rule [bytes-concat-lookup-right]:
        (A:Bytes +Bytes B:Bytes) [I] => B [I -Int lengthBytes(A)]
      requires lengthBytes(A) <=Int I
      [simplification, preserves-definedness]

endmodule