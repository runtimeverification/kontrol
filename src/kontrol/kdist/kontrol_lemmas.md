Kontrol Auxiliary Lemmas
==============

The provided K Lemmas define auxiliary lemmas that facilitate reasoning in Kontrol.
These lemmas are to be upstreamed to KEVM and removed from Kontrol once they are no longer needed.

```k
requires "foundry.md"

module KONTROL-AUX-LEMMAS
    imports EVM
    imports FOUNDRY
    imports INT-SYMBOLIC
    imports MAP-SYMBOLIC
    imports SET-SYMBOLIC

    syntax StepSort ::= Int
                      | Bool
                      | Bytes
                      | Map
                      | Set
 // -------------------------

    syntax KItem ::= runLemma ( StepSort )
                   | doneLemma( StepSort )
 // --------------------------------------
    rule <k> runLemma(T) => doneLemma(T) ... </k>

    syntax Int ::= "ethMaxWidth" [macro]
    syntax Int ::= "ethUpperBound" [macro]
 // --------------------------------------
    rule ethMaxWidth => 96
    rule ethUpperBound => 2 ^Int ethMaxWidth
 // ----------------------------------------

    // ==Int
    rule [int-eq-refl]: X ==Int X => true [simplification]

    // *Int
    rule A *Int B ==Int 0 => A ==Int 0 orBool B ==Int 0 [simplification]

    // /Int
    rule 0 /Int B         => 0        requires B =/=Int 0                 [simplification, preserves-definedness]
    rule A /Int B ==Int 0 => A <Int B requires 0 <=Int A andBool 0 <Int B [simplification, preserves-definedness]

    rule ( A *Int B ) /Int C => ( A /Int C ) *Int B
      requires 0 <=Int A andBool (notBool C ==Int 0) andBool A modInt C ==Int 0
      [simplification, concrete(A, C), preserves-definedness]

    // /Word
    rule  _ /Word W1 => 0          requires W1  ==Int 0 [simplification]
    rule W0 /Word W1 => W0 /Int W1 requires W1 =/=Int 0 [simplification, preserves-definedness]

    // Further /Int and /Word arithmetic
    rule ( X *Int Y ) /Int Y => X requires Y =/=Int 0              [simplification, preserves-definedness]
    rule ( X *Int Y ) /Int X => Y requires X =/=Int 0              [simplification, preserves-definedness]
    rule ( X ==Int ( X *Int Y ) /Word Y ) orBool Y ==Int 0 => true [simplification, preserves-definedness]
    rule ( X ==Int ( Y *Int X ) /Word Y ) orBool Y ==Int 0 => true [simplification, preserves-definedness]
    rule ( 0 ==Int          0   /Word Y ) orBool Y ==Int 0 => true [simplification, preserves-definedness]

    rule A <=Int B /Int C =>         A  *Int C <=Int B requires 0 <Int C [simplification, preserves-definedness]
    rule A  <Int B /Int C => (A +Int 1) *Int C <=Int B requires 0 <Int C [simplification, preserves-definedness]
    rule A  >Int B /Int C =>         A  *Int C  >Int B requires 0 <Int C [simplification, preserves-definedness]
    rule A >=Int B /Int C => (A +Int 1) *Int C  >Int B requires 0 <Int C [simplification, preserves-definedness]

    rule B /Int C >=Int A =>         A  *Int C <=Int B requires 0 <Int C [simplification, preserves-definedness]
    rule B /Int C  >Int A => (A +Int 1) *Int C <=Int B requires 0 <Int C [simplification, preserves-definedness]
    rule B /Int C  <Int A =>         A  *Int C  >Int B requires 0 <Int C [simplification, preserves-definedness]
    rule B /Int C <=Int A => (A +Int 1) *Int C  >Int B requires 0 <Int C [simplification, preserves-definedness]

    // More specialised /Int and /Word arithmetic
    rule ( X ==Int ( X *Int ( Y +Int C ) ) /Word ( Y +Int C ) ) orBool Y ==Int D => true
      requires C +Int D ==Int 0 [simplification, preserves-definedness]

    // modInt
    rule (X *Int Y) modInt Z => 0 requires X modInt Z ==Int 0 [simplification, concrete(X, Z), preserves-definedness]

    // >>Int
    rule [shift-to-div]: X >>Int N => X /Int (2 ^Int N)
      requires 0 <=Int X andBool 0 <=Int N [simplification(60), concrete(N)]

    // Boolean equality
    rule B ==K false => notBool B [simplification(30), comm]
    rule B ==K true  =>         B [simplification(30), comm]

    //
    // .Bytes
    //
    rule .Bytes ==K b"" => true [simplification, comm]

    rule    b"" ==K #buf(X, _) +Bytes _ => false requires 0 <Int X [simplification, concrete(X), comm]
    rule    b"" ==K _ +Bytes #buf(X, _) => false requires 0 <Int X [simplification, concrete(X), comm]
    rule .Bytes ==K #buf(X, _) +Bytes _ => false requires 0 <Int X [simplification, concrete(X), comm]
    rule .Bytes ==K _ +Bytes #buf(X, _) => false requires 0 <Int X [simplification, concrete(X), comm]

    rule [concat-neutral-left]:  b"" +Bytes B:Bytes => B:Bytes [simplification]
    rule [concat-neutral-right]: B:Bytes +Bytes b"" => B:Bytes [simplification]

    //
    // Equality of +Bytes
    //
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

    //
    // Specific simplifications
    //
    rule X &Int ( Y *Int Z ) => 0
    requires 0 <=Int X andBool 0 <=Int Y andBool 0 <=Int Z
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool Y ==Int 2 ^Int log2Int(Y)
     andBool log2Int(X +Int 1) <=Int log2Int(Y)
     [simplification, concrete(X, Y), preserves-definedness]

    rule [mul-cancel-10-le]:
      A *Int B <=Int C *Int D => (A /Int 10) *Int B <=Int (C /Int 10) *Int D
      requires 0 <=Int A andBool 0 <=Int C andBool A modInt 10 ==Int 0 andBool C modInt 10 ==Int 0
      [simplification, concrete(A, C), preserves-definedness]

    rule [mul-cancel-10-lt]:
      A *Int B <Int C *Int D => (A /Int 10) *Int B <Int (C /Int 10) *Int D
      requires 0 <=Int A andBool 0 <=Int C andBool A modInt 10 ==Int 0 andBool C modInt 10 ==Int 0
      [simplification, concrete(A, C), preserves-definedness]

    //
    //  Overflows and ranges
    //
    rule X <=Int A +Int B => true requires X <=Int 0 andBool 0 <=Int A andBool 0 <=Int B [concrete(X), simplification, preserves-definedness]
    rule X <=Int A *Int B => true requires X <=Int 0 andBool 0 <=Int A andBool 0 <=Int B [concrete(X), simplification, preserves-definedness]
    rule X <=Int A /Int B => true requires X <=Int 0 andBool 0 <=Int A andBool 0  <Int B [concrete(X), simplification, preserves-definedness]

    rule X <Int A +Int B => true requires X <=Int 0 andBool 0  <Int A andBool 0 <=Int B [concrete(X), simplification]
    rule X <Int A +Int B => true requires X <=Int 0 andBool 0 <=Int A andBool 0  <Int B [concrete(X), simplification]
    rule X <Int A *Int B => true requires X <=Int 0 andBool 0  <Int A andBool 0  <Int B [concrete(X), simplification]

    //
    // #lookup
    //
    rule M:Map [ K1 <- _ ] [ K1 <- V2 ]                                                                               => M:Map [ K1 <- V2 ] [simplification]
    rule M:Map [ K1 <- _ ] [ K2 <- V2 ] [ K1 <- V3 ]                                                                  => M:Map [ K2 <- V2 ] [ K1 <- V3 ] [simplification]
    rule M:Map [ K1 <- _ ] [ K2 <- V2 ] [ K3 <- V3 ] [ K1 <- V4 ]                                                     => M:Map [ K2 <- V2 ] [ K3 <- V3 ] [ K1 <- V4 ] [simplification]
    rule M:Map [ K1 <- _ ] [ K2 <- V2 ] [ K3 <- V3 ] [ K4 <- V4 ] [ K1 <- V5 ]                                        => M:Map [ K2 <- V2 ] [ K3 <- V3 ] [ K4 <- V4 ] [ K1 <- V5 ] [simplification]
    rule M:Map [ K1 <- _ ] [ K2 <- V2 ] [ K3 <- V3 ] [ K4 <- V4 ] [ K5 <- V5 ] [ K1 <- V6 ]                           => M:Map [ K2 <- V2 ] [ K3 <- V3 ] [ K4 <- V4 ] [ K5 <- V5 ] [ K1 <- V6 ] [simplification]
    rule M:Map [ K1 <- _ ] [ K2 <- V2 ] [ K3 <- V3 ] [ K4 <- V4 ] [ K5 <- V5 ] [ K6 <- V6 ] [ K1 <- V7 ]              => M:Map [ K2 <- V2 ] [ K3 <- V3 ] [ K4 <- V4 ] [ K5 <- V5 ] [ K6 <- V6 ] [ K1 <- V7 ] [simplification]
    rule M:Map [ K1 <- _ ] [ K2 <- V2 ] [ K3 <- V3 ] [ K4 <- V4 ] [ K5 <- V5 ] [ K6 <- V6 ] [ K7 <- V7 ] [ K1 <- V8 ] => M:Map [ K2 <- V2 ] [ K3 <- V3 ] [ K4 <- V4 ] [ K5 <- V5 ] [ K6 <- V6 ] [ K7 <- V7 ] [ K1 <- V8 ] [simplification]

    rule lengthBytes ( #padToWidth ( 32 , #asByteStack ( VALUE ) ) ) => 32
        requires #rangeUInt(256, VALUE)
        [simplification]

    rule X -Int Y <=Int Z => true
        requires X <=Int Z
         andBool 0 <=Int Y
        [simplification, smt-lemma]

    rule X modInt pow256 => X
        requires 0 <=Int X
         andBool X <=Int maxUInt128
        [simplification]

    rule X *Int Y <Int Z => true
        requires #rangeUInt(256, X)
         andBool #rangeUInt(256, Y)
         andBool #rangeUInt(256, Z)
         andBool X <Int 2 ^Int ( log2Int(Z) /Int 2 )
         andBool Y <Int 2 ^Int ( log2Int(Z) /Int 2 )
        [simplification, concrete(Z)]

    //
    // NEW LEMMAS
    //

    rule [symb-program-index]:
      M:Bytes [ N:Int ] => #asWord ( #range(M, N, 1) )
      requires 0 <=Int N andBool N <Int lengthBytes(M)
      [simplification(60), symbolic(M), concrete(N), preserves-definedness]

    rule X *Int Y <=Int Z => Y <Int ( Z +Int 1 ) /Int X
      requires 0 <Int X andBool 0 <=Int Z andBool ( Z +Int 1) modInt X ==Int 0
      [simplification, concrete(X, Z), preserves-definedness]

endmodule
```