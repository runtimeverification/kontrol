requires "../contracts.k"
// requires "foundry.md"

module TEST-LEMMAS
//   imports FOUNDRY

  imports S2KFreshIntTest-CONTRACT

//   rule 
//   #range ( BYTES1:Bytes +Bytes BYTES2 +Bytes (BYTES3:Bytes [ KEY <- VAL ]) +Bytes BYTES4, OFFSET, LEN ) => 
//   #range ( BYTES1:Bytes +Bytes BYTES2 +Bytes (BYTES3:Bytes [ KEY <- VAL ])              , OFFSET, LEN )
//   requires lengthBytes(BYTES1) +Int lengthBytes(BYTES2) >=Int OFFSET +Int LEN
//   [simplification]
// 
//   rule 
//   #range ( BYTES1:Bytes +Bytes BYTES2 +Bytes (BYTES3:Bytes [ KEY <- VAL ]), OFFSET                         , LEN ) => 
//   #range (                     BYTES2 +Bytes (BYTES3:Bytes [ KEY <- VAL ]), OFFSET -Int lengthBytes(BYTES1), LEN )
//   requires lengthBytes(BYTES1) <=Int OFFSET
//   [simplification]




//   rule 2 <Int #asWord ( #range ( BYTES:Bytes +Bytes
//   b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05"
//   +Bytes (BYTES:Bytes [ 2 <- 170 ]) +Bytes b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" , 32 , 32 ) )
//   => true
//   requires lengthBytes(BYTES) ==Int 5 [simplification]

// rule 2 <Int #asWord ( #range ( padRightBytes ( b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05" +Bytes BYTES:Bytes +Bytes b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05" +Bytes BYTES:Bytes +Bytes b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" , 259 , 0 ) [ 258 <- 170 ] , 224 , 32 ) ) => 
// true
// requires lengthBytes(BYTES) ==Int 5 [simplification]


//   rule lengthBytes(B1:Bytes +Bytes B2:Bytes) => lengthBytes(B1) +Int lengthBytes(B2) [simplification]
// 
//   rule lengthBytes(Int2Bytes(N:Int, _:Int, _:Endianness)) => N [simplification]


//   rule #asWord(Int2Bytes(_:Int, N:Int, _:Endianness)) <=Int M:Int => true requires N <=Int M [simplification]
// 
//   rule chop( #asWord( B:Bytes ) +Int M:Int ) => #asWord( B:Bytes ) +Int M:Int 
//   requires (2 ^Int lengthBytes(B)) -Int 1 +Int M <=Int (2 ^Int 256) -Int 1 [simplification]
// 
//   rule #range(B1:Bytes +Bytes B2:Bytes, N:Int, LEN:Int) 
//     => #range(B2, N -Int lengthBytes(B1), LEN) 
//     requires lengthBytes(B1) <=Int N [simplification]
// 
//   rule #range(B1:Bytes +Bytes B2:Bytes, N:Int, LEN:Int) 
//     => #range(B1, N, LEN) 
//     requires lengthBytes(B1) >=Int N +Int LEN [simplification]
// 
//   rule #range( padRightBytes( B1:Bytes +Bytes B2:Bytes, PAD_LEN:Int, PAD_BYTE:Int), N:Int, LEN:Int) 
//     => #range( padRightBytes( B2:Bytes, PAD_LEN -Int lengthBytes(B1), PAD_BYTE), N -Int lengthBytes(B1), LEN) 
//     requires lengthBytes(B1) <=Int N [simplification]
// 
//   rule #range( padRightBytes( B:Bytes, _:Int, _:Int), N:Int, LEN:Int) 
//     => #range(B:Bytes, N, LEN) 
//     requires N +Int LEN <Int lengthBytes(B) [simplification]
// 
//   rule #range(B:Bytes [KEY:Int <- _:Int], N:Int, LEN:Int) => #range(B, N, LEN) 
//   requires N +Int LEN <=Int KEY [simplification]
// 
//   rule #range(B:Bytes [KEY:Int <- _:Int], N:Int, LEN:Int) => #range(B, N, LEN) 
//   requires N >Int KEY [simplification]
// 
//   rule padRightBytes(B:Bytes, TARGET_LEN:Int, _:Int) => B
//   requires lengthBytes(B) >=Int TARGET_LEN [simplification]

//   rule (B1:Bytes +Bytes B2:Bytes)[ KEY:Int <- VAL:Int ] => (B1[ KEY <- VAL ]) +Bytes B2
//   requires KEY <Int lengthBytes(B1) [simplification]
// 
//   rule (B1:Bytes +Bytes B2:Bytes)[ KEY:Int <- VAL:Int ] => B1 +Bytes (B2[ (KEY -Int lengthBytes(B1)) <- VAL ])
//   requires KEY >=Int lengthBytes(B1) [simplification]


// rule #Ceil (BYTES:Bytes [KEY:Int <- VAL:Int]) => { true #Equals KEY <Int lengthBytes(BYTES) } #And { true #Equals VAL <=Int 255 } #And #Ceil(BYTES) #And #Ceil(KEY) #And #Ceil(VAL) [simplification]

  rule notMaxUInt248 &Int #asWord( BYTES:Bytes ) => #asWord( #range(BYTES, 0, 1) +Bytes Int2Bytes(31, 0, BE) ) [simplification]

  rule #range( BYTES:Bytes [OFFSET:Int <- N:Int], OFFSET, 1) => Int2Bytes(1, N, BE) [simplification]

  rule #range( BYTES:Bytes [OFFSET1:Int <- _:Int], OFFSET2, 1) => #range( BYTES:Bytes, OFFSET2, 1) 
  requires notBool (OFFSET1 ==Int OFFSET2) [simplification]

endmodule
