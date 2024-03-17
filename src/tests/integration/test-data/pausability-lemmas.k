requires "evm.md"
requires "foundry.md"

module PAUSABILITY-LEMMAS [symbolic]
    imports BOOL
    imports FOUNDRY
    imports INT-SYMBOLIC

    syntax StepSort ::= Int
                      | Bool
                      | Bytes
                      | Set
 // ------------------------

    syntax KItem ::= runLemma ( StepSort )
                   | doneLemma( StepSort )
 // --------------------------------------
    rule <k> runLemma(T) => doneLemma(T) ... </k>

    // We need to enforce some limit on the length of bytearrays
    // and indices into bytearrays in order to avoid chop-reasoning
    syntax Int ::= "maxBytesLength" [alias]
    rule maxBytesLength => 9223372036854775808


    // Deconstruction of <<Int into #buf
    rule X <<Int Y => #asWord ( #buf ( 32 -Int (Y /Int 8) , X ) +Bytes #buf ( Y /Int 8 , 0 ) )
      requires 0 <=Int X andBool X <Int 2 ^Int (256 -Int Y)
       andBool 0 <=Int Y andBool Y <=Int 256 andBool Y modInt 8 ==Int 0
      [simplification, concrete(Y)]

    //
    // Arithmetic
    //

    // Cancellativity #1
    rule A +Int B -Int B +Int C => A +Int C [simplification]

    // Cancellativity #2
    rule A -Int B +Int C -Int D +Int B +Int E => A -Int D +Int C +Int E [simplification]

    // Cancellativity #3
    rule ( A +Int B ) +Int C <=Int ( D +Int B ) +Int E => A +Int C <=Int D +Int E [simplification]

    // Cancellativity #4
    rule A +Int B <=Int ( A +Int C ) +Int D => B <=Int C +Int D [simplification]

    // Cancellativity #5
    rule A +Int ( (B -Int A) +Int C ) => B +Int C [simplification]

    // Cancellativity #6
    rule (A -Int B) -Int (C -Int B) => A -Int C [simplification]
  
    // Upper bound on (pow256 - 32) &Int lengthBytes(X)
    rule notMaxUInt5 &Int Y <=Int Y => true
      requires 0 <=Int Y
      [simplification]

    // Bounds on notMaxUInt5 &Int ( X +Int 31 )
    // Note: upstream in the next round
    rule X <=Int   notMaxUInt5 &Int ( X +Int 31 )          => true requires 0 <=Int X                   [simplification]
    rule X <=Int   notMaxUInt5 &Int ( Y +Int 31 )          => true requires X <=Int 0 andBool 0 <=Int Y [simplification, concrete(X)]
    rule X <=Int ( notMaxUInt5 &Int ( X +Int 31 ) ) +Int Y => true requires 0 <=Int X andBool 0 <=Int Y [simplification, concrete(Y)]

    rule notMaxUInt5 &Int X +Int 31 <Int Y => true requires 0 <=Int X andBool X +Int 32 <=Int Y [simplification, concrete(Y)]

    rule notMaxUInt5 &Int X +Int 31 <Int X +Int 32 => true requires 0 <=Int X [simplification]

    //
    // #asWord
    //

    // Move to function parameters
    rule { #asWord ( X ) #Equals #asWord ( Y ) } => #Top
      requires X ==K Y
      [simplification]

    // #asWord ignores leading zeros
    rule #asWord ( BA1 +Bytes BA2 ) => #asWord ( BA2 )
      requires #asInteger(BA1) ==Int 0
      [simplification, concrete(BA1)]


    // Equality and #range
    rule #asWord ( #range ( #buf ( 32 , _X:Int ) , S:Int , W:Int ) ) ==Int Y:Int => false
        requires S +Int W <=Int 32
         andBool (2 ^Int (8 *Int W)) <=Int Y
        [concrete(S, W, Y), simplification]

    // Conversion from bytes always yields a non-negative integer
    rule 0 <=Int #asInteger ( _ ) => true [simplification]

    //
    // #padRightToWidth
    //

    rule #padRightToWidth (W, X) => X +Bytes #buf(W -Int lengthBytes(X), 0)
      [concrete(W), simplification]

    //
    // #range(M, START, WIDTH)
    //

    // Parameter equality
    rule { #range (A, B, C) #Equals #range (A, B, D) } => #Top
      requires C ==Int D
      [simplification]

    //
    // Bytes indexing and update
    //

    rule B:Bytes [ X:Int ] => #asWord ( #range (B, X, 1) )
      requires X <=Int lengthBytes(B)
      [simplification(40)]

    // Empty update has no effect
    rule B:Bytes [ START:Int := b"" ] => B
      requires 0 <=Int START andBool START <=Int lengthBytes(B)
      [simplification]

    // Consecutive quasi-contiguous byte-array update
    rule B [ S1 := B1 ] [ S2 := B2 ] => B [ S1 := #range(B1, 0, S2 -Int S1) +Bytes B2 ]
      requires 0 <=Int S1 andBool S1 <=Int S2 andBool S2 <=Int S1 +Int lengthBytes(B1)
      [simplification]

    // Parameter equality: byte-array update
    rule { B1:Bytes [ S1:Int := B2:Bytes ] #Equals B3:Bytes [ S2:Int := B4:Bytes ] } => #Top
      requires B1 ==K B3 andBool S1 ==Int S2 andBool B2 ==K B4
      [simplification]

    //
    // SUMMARIES
    //

    // This rule cannot be used without the [symbolic] tag because it uses
    // "existentials", which is not correct, it uses variables that are learnt
    // from the requires and not from the structure

    // copy-memory-to-memory
    rule [test-copy-memory-to-memory-summary]:
      <k> #execute ... </k>
      <useGas> false </useGas>
      <schedule> SHANGHAI </schedule>
      <jumpDests> JUMPDESTS </jumpDests>
      // The program and program counter are symbolic, focusing on the part we will be executing (CP)
      <program> PROGRAM </program>
      <pc> PCOUNT => PCOUNT +Int 44 </pc>
      // The word stack has the appropriate form, as per the compiled code
      <wordStack> SRC : DEST : LENGTH : WS </wordStack>
      // The program copies LENGTH bytes of memory from SRC +Int 32 to DEST +Int OFFSET,
      // padded with 32 zeros in case LENGTH is not divisible by 32
      <localMem>
        LM => LM [ DEST := #range ( LM, SRC, LENGTH ) +Bytes
                                   #buf ( ( ( notMaxUInt5 &Int ( LENGTH +Int maxUInt5 ) ) -Int LENGTH ) , 0 ) +Bytes
                                   #buf ( ( ( ( 32 -Int ( ( notMaxUInt5 &Int ( LENGTH +Int maxUInt5 ) ) -Int LENGTH ) ) ) modInt 32 ), 0 ) ]
      </localMem>
      requires
       // The current program we are executing differs from the original one only in the hardcoded jump addresses,
       // which are now relative to PCOUNT, and the hardcoded offset, which is now symbolic.
               #range(PROGRAM, PCOUNT, 44) ==K b"[`\x00[\x83\x81\x10\x15a\n\x9fW\x81\x81\x01Q\x83\x82\x01R` \x01a\n\x87V[\x83\x81\x11\x15a\n\xaeW`\x00\x84\x84\x01R[P"
                                               [ 09 := #buf(2, PCOUNT +Int 27) ]
                                               [ 24 := #buf(2, PCOUNT +Int  3) ]
                                               [ 33 := #buf(2, PCOUNT +Int 42) ]

       // Various well-formedness constraints. In particular, the maxBytesLength-related ones are present to
       // remove various chops that would otherwise creep into the execution, and are reasonable since byte
       // arrays in actual programs would never reach that size.
       andBool 0 <=Int PCOUNT
       andBool 0 <=Int LENGTH andBool LENGTH <Int maxBytesLength
       andBool 0 <=Int SRC    andBool SRC    <Int maxBytesLength
       andBool 0 <=Int DEST   andBool DEST   <Int maxBytesLength
       andBool #sizeWordStack(WS) <=Int 1015

       andBool SRC +Int LENGTH <=Int DEST // No overlap between source and destination
       andBool DEST <=Int lengthBytes(LM) // Destination starts within current memory
       // All JUMPDESTs in the program are valid
       andBool (PCOUNT +Int 3) in JUMPDESTS andBool (PCOUNT +Int 27) in JUMPDESTS andBool (PCOUNT +Int 42) in JUMPDESTS
       andBool PCOUNT +Int 42 <Int 2 ^Int 16  // and fit into two bytes
      [priority(30), concrete(JUMPDESTS, PROGRAM, PCOUNT), preserves-definedness]

endmodule