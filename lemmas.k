requires "../contracts.k"

module TEST-LEMMAS

  imports S2KFreshIntTest-CONTRACT

  rule lengthBytes(Int2Bytes(N:Int, _:Int, _:Endianness)) => N [simplification]

//   rule #asWord( Int2Bytes(N:Int, _:Int , _:Endianness) ) <=Int M:Int => true requires (2 ^Int (N *Int 8)) -Int 1 <= M [simplification]

  rule #asWord(Int2Bytes(_:Int, N:Int, _:Endianness)) <=Int M:Int => true requires N <=Int M [simplification]

// chop ( ( #asWord ( Int2Bytes ( 32 , lengthBytes ( ?BYTES:Bytes ) , BE ) ) +Int maxUInt5 ) )

  rule chop( #asWord( B:Bytes ) +Int M:Int ) => #asWord( B:Bytes ) +Int M:Int 
  requires (2 ^Int lengthBytes(B)) -Int 1 +Int M <=Int (2 ^Int 256) -Int 1 [simplification]

  rule #range(B1:Bytes +Bytes B2:Bytes, N:Int, LEN:Int) 
    => #range(B2, N -Int lengthBytes(B1), LEN) 
    requires lengthBytes(B1) <=Int N [simplification]

  rule #range(B1:Bytes +Bytes B2:Bytes, N:Int, LEN:Int) 
    => #range(B1, N, LEN) 
    requires lengthBytes(B1) >=Int N +Int LEN [simplification]

  rule #range( padRightBytes( B1:Bytes +Bytes B2:Bytes, PAD_LEN:Int, PAD_BYTE:Int), N:Int, LEN:Int) 
    => #range( padRightBytes( B2:Bytes, PAD_LEN -Int lengthBytes(B1), PAD_BYTE), N -Int lengthBytes(B1), LEN) 
    requires lengthBytes(B1) <=Int N [simplification]

  rule #range( padRightBytes( B:Bytes, _:Int, _:Int), N:Int, LEN:Int) 
    => #range(B:Bytes, N, LEN) 
    requires N +Int LEN <Int lengthBytes(B) [simplification]

  rule #range(B:Bytes [KEY:Int <- _:Int], N:Int, LEN:Int) => #range(B, N, LEN) 
  requires N +Int LEN <=Int KEY [simplification]

  rule #range(B:Bytes [KEY:Int <- _:Int], N:Int, LEN:Int) => #range(B, N, LEN) 
  requires N >Int KEY [simplification]

  rule padRightBytes(B:Bytes, TARGET_LEN:Int, _:Int) => B
  requires lengthBytes(B) >=Int TARGET_LEN [simplification]

  rule (B1:Bytes +Bytes B2:Bytes)[ KEY:Int <- VAL:Int ] => (B1[ KEY <- VAL ]) +Bytes B2
  requires KEY <Int lengthBytes(B1) [simplification]

  rule (B1:Bytes +Bytes B2:Bytes)[ KEY:Int <- VAL:Int ] => B1 +Bytes (B2[ (KEY -Int lengthBytes(B1)) <- VAL ])
  requires KEY >=Int lengthBytes(B1) [simplification]


endmodule
