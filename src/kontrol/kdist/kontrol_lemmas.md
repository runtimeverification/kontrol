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

    // chop and +Int
    rule [chop-plus]: chop (A +Int B) ==Int 0 => A ==Int (-1) *Int B
      requires #rangeUInt(256, A) andBool #rangeUInt(256, (-1) *Int B)
      [concrete(B), simplification, comm]

    // chop and -Int
    rule [chop-zero-minus]: chop (0 -Int A) ==Int B => A ==Int (pow256 -Int B) modInt pow256
      requires #rangeUInt(256, A) andBool #rangeUInt(256, B)
      [concrete(B), simplification, comm, preserves-definedness]

    // ==Int
    rule [int-eq-refl]: X ==Int X => true [simplification]

    // *Int
    rule A *Int B ==Int 0 => A ==Int 0 orBool B ==Int 0 [simplification]

    rule A *Int B => B *Int A [simplification(30), symbolic(A), concrete(B)]

    // /Int
    rule 0 /Int B         => 0        requires B =/=Int 0                 [simplification, preserves-definedness]
    rule A /Int B ==Int 0 => A <Int B requires 0 <=Int A andBool 0 <Int B [simplification, preserves-definedness]

    rule ( A *Int B ) /Int C => ( A /Int C ) *Int B requires A modInt C ==Int 0 [simplification, concrete(A, C), preserves-definedness]

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

    // Further generalization of: maxUIntXXX &Int #asWord ( BA )
    rule X &Int #asWord ( BA ) => #asWord ( #range(BA, lengthBytes(BA) -Int (log2Int(X +Int 1) /Int 8), log2Int(X +Int 1) /Int 8) )
    requires #rangeUInt(256, X)
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool log2Int (X +Int 1) modInt 8 ==Int 0
     andBool (log2Int (X +Int 1)) /Int 8 <=Int lengthBytes(BA) andBool lengthBytes(BA) <=Int 32
     [simplification, concrete(X), preserves-definedness]

    // #asWord
    rule #asWord ( B1 +Bytes B2 ) => #asWord ( B2 )
        requires #asWord ( B1 ) ==Int 0
        [simplification, concrete(B1)]

    rule #asWord( BA ) >>Int N => #asWord( #range ( BA, 0, lengthBytes( BA ) -Int ( N /Int 8 ) ) )
    requires 0 <=Int N andBool N modInt 8 ==Int 0
    [simplification, concrete(N), preserves-definedness]

    // >>Int
    rule [shift-to-div]: X >>Int N => X /Int (2 ^Int N) [simplification(60), concrete(N)]

    // Boolean equality
    rule B ==K false => notBool B [simplification(30), comm]
    rule B ==K true  =>         B [simplification(30), comm]

    // bool2Word
    rule bool2Word(X)  ==Int 0 => notBool X [simplification(30), comm]
    rule bool2Word(X) =/=Int 0 => X         [simplification(30), comm]
    rule bool2Word(X)  ==Int 1 => X         [simplification(30), comm]
    rule bool2Word(X) =/=Int 1 => notBool X [simplification(30), comm]

    rule [bool2Word-lt-true]:  bool2Word(_:Bool) <Int X:Int => true      requires 1 <Int X [simplification(30), concrete(X)]
    rule [bool2Word-lt-one]:   bool2Word(B:Bool) <Int 1     => notBool B                   [simplification(30)]
    rule [bool2Word-gt-zero]:  0 <Int bool2Word(B:Bool)     => B                           [simplification(30)]
    rule [bool2Word-gt-false]: X:Int <Int bool2Word(_:Bool) => false     requires 1 <Int X [simplification(30), concrete(X)]

    rule 0 <=Int bool2Word(X) => true [simplification, smt-lemma]
    rule bool2Word(X) <=Int 1 => true [simplification, smt-lemma]

    rule bool2Word ( X ) xorInt bool2Word ( Y ) => bool2Word ( (X andBool notBool Y) orBool (notBool X andBool Y) ) [simplification]
    rule 1 xorInt bool2Word ( X ) => 1 -Int bool2Word ( X ) [simplification, comm]
    rule 0 xorInt bool2Word ( X ) => bool2Word ( X ) [simplification, comm]

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
    // Alternative memory update
    //
    rule [memUpdate-concat-in-right]: (B1 +Bytes B2) [ S := B ] => B1 +Bytes (B2 [ S -Int lengthBytes(B1) := B ])
      requires lengthBytes(B1) <=Int S
      [simplification(40)]

    rule [memUpdate-concat-in-left]: (B1 +Bytes B2) [ S := B ] => (B1 [S := B]) +Bytes B2
      requires 0 <=Int S andBool S +Int lengthBytes(B) <=Int lengthBytes(B1)
      [simplification(45)]

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
    rule X &Int #asWord ( BA ) ==Int Y:Int => true
    requires 0 <=Int X andBool X <Int 2 ^Int (8 *Int lengthBytes(BA))
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool log2Int (X +Int 1) modInt 8 ==Int 0
     andBool #asWord ( #range(BA, lengthBytes(BA) -Int (log2Int(X +Int 1) /Int 8), log2Int(X +Int 1) /Int 8) ) ==Int Y:Int
     [simplification, concrete(X), comm, preserves-definedness]

    rule X &Int #asWord ( BA ) ==Int Y:Int => false
    requires 0 <=Int X andBool X <Int 2 ^Int (8 *Int lengthBytes(BA))
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool log2Int (X +Int 1) modInt 8 ==Int 0
     andBool notBool #asWord ( #range(BA, lengthBytes(BA) -Int (log2Int(X +Int 1) /Int 8), log2Int(X +Int 1) /Int 8) ) ==Int Y:Int
     [simplification, concrete(X), comm, preserves-definedness]

    rule X &Int #asWord ( BA ) <Int Y:Int => true
    requires 0 <=Int X andBool X <Int 2 ^Int (8 *Int lengthBytes(BA))
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool log2Int (X +Int 1) modInt 8 ==Int 0
     andBool #asWord ( #range(BA, lengthBytes(BA) -Int (log2Int(X +Int 1) /Int 8), log2Int(X +Int 1) /Int 8) ) <Int Y:Int
     [simplification, concrete(X), preserves-definedness]

    rule X &Int #asWord ( BA ) <Int Y:Int => false
    requires 0 <=Int X andBool X <Int 2 ^Int (8 *Int lengthBytes(BA))
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool log2Int (X +Int 1) modInt 8 ==Int 0
     andBool notBool #asWord ( #range(BA, lengthBytes(BA) -Int (log2Int(X +Int 1) /Int 8), log2Int(X +Int 1) /Int 8) ) <Int Y:Int
     [simplification, concrete(X), preserves-definedness]

    rule X &Int #asWord ( BA ) <=Int Y:Int => true
    requires 0 <=Int X andBool X <Int 2 ^Int (8 *Int lengthBytes(BA))
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool log2Int (X +Int 1) modInt 8 ==Int 0
     andBool #asWord ( #range(BA, lengthBytes(BA) -Int (log2Int(X +Int 1) /Int 8), log2Int(X +Int 1) /Int 8) ) <=Int Y:Int
     [simplification, concrete(X), preserves-definedness]

    rule X &Int #asWord ( BA ) <=Int Y:Int => false
    requires 0 <=Int X andBool X <Int 2 ^Int (8 *Int lengthBytes(BA))
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool log2Int (X +Int 1) modInt 8 ==Int 0
     andBool notBool #asWord ( #range(BA, lengthBytes(BA) -Int (log2Int(X +Int 1) /Int 8), log2Int(X +Int 1) /Int 8) ) <=Int Y:Int
     [simplification, concrete(X), preserves-definedness]

    rule X &Int ( Y *Int Z ) => 0
    requires 0 <=Int X andBool 0 <=Int Y andBool 0 <=Int Z
     andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
     andBool Y ==Int 2 ^Int log2Int(Y)
     andBool log2Int(X +Int 1) <=Int log2Int(Y)
     [simplification, concrete(X, Y), preserves-definedness]

    rule chop ( X *Int Y ) => X *Int Y
      requires 0 <=Int X andBool X <Int ethUpperBound
       andBool 0 <=Int Y andBool Y <Int 2 ^Int ( 256 -Int ethMaxWidth )
       [simplification]

    rule [mul-overflow-check]:
      X ==Int chop ( X *Int Y ) /Int Y => X *Int Y <Int pow256
      requires #rangeUInt(256, X) andBool 0 <Int Y
      [simplification, comm, preserves-definedness]

    rule [mul-overflow-check-ML]:
      { X #Equals chop ( X *Int Y ) /Int Y } => { true #Equals X *Int Y <Int pow256 }
      requires #rangeUInt(256, X) andBool 0 <Int Y
      [simplification, preserves-definedness]

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

    rule [chop-no-overflow-add-l]: X:Int <=Int chop ( X +Int Y:Int ) => X +Int Y <Int pow256 requires #rangeUInt(256, X) andBool #rangeUInt(256, Y)             [simplification]
    rule [chop-no-overflow-add-r]: X:Int <=Int chop ( Y +Int X:Int ) => X +Int Y <Int pow256 requires #rangeUInt(256, X) andBool #rangeUInt(256, Y)             [simplification]
    rule [chop-no-overflow-mul-l]: X:Int <=Int chop ( X *Int Y:Int ) => X *Int Y <Int pow256 requires #rangeUInt(256, X) andBool #rangeUInt(256, Y)             [simplification]
    rule [chop-no-overflow-mul-r]: X:Int <=Int chop ( Y *Int X:Int ) => X *Int Y <Int pow256 requires #rangeUInt(256, X) andBool #rangeUInt(256, Y)             [simplification]
    rule [chop-no-overflow-div]:   X:Int <=Int chop ( X /Int Y:Int ) => X /Int Y <Int pow256 requires #rangeUInt(256, X) andBool 0 <Int Y andBool Y <Int pow256 [simplification]

    // Index of first bit that equals one
    syntax Int ::=  #getFirstOneBit(Int) [function, total]

    rule [gfo-succ]: #getFirstOneBit(X:Int) => log2Int ( X &Int ( ( maxUInt256 xorInt X ) +Int 1 ) ) requires          #rangeUInt(256, X) andBool X =/=Int 0
    rule [gfo-fail]: #getFirstOneBit(X:Int) => -1                                                    requires notBool (#rangeUInt(256, X) andBool X =/=Int 0)

    // Index of first bit that equals zero
    syntax Int ::= #getFirstZeroBit(Int) [function, total]

    rule [gfz-succ]: #getFirstZeroBit(X:Int) => #getFirstOneBit ( maxUInt256 xorInt X ) requires         #rangeUInt(256, X)
    rule [gfz-fail]: #getFirstZeroBit(X:Int) => -1                                      requires notBool #rangeUInt(256, X)

    // Slot updates are performed by the compiler with the help of masks,
    // which are 256-bit integers of the form 11111111100000000000111111111111111
    //                                                 |- WIDTH -||-   SHIFT   -|

    // Shift of a mask, in bits and in bytes
    syntax Int ::= #getMaskShiftBits(Int)  [function, total]
    syntax Int ::= #getMaskShiftBytes(Int) [function, total]

    rule [gms-bits]: #getMaskShiftBits(X:Int)  => #getFirstZeroBit(X) [concrete(X), simplification]

    rule [gms-bits-succ]: #getMaskShiftBytes(X:Int) => #getFirstZeroBit(X) /Int 8 requires           #getMaskShiftBits(X) modInt 8 ==Int 0   [concrete(X), simplification, preserves-definedness]
    rule [gms-bits-fail]: #getMaskShiftBytes(X:Int) => -1                         requires notBool ( #getMaskShiftBits(X) modInt 8 ==Int 0 ) [concrete(X), simplification, preserves-definedness]

    // Width of a mask, in bits and in bytes
    syntax Int ::= #getMaskWidthBits(Int)  [function, total]
    syntax Int ::= #getMaskWidthBytes(Int) [function, total]

    rule [gmw-bits-succ-1]: #getMaskWidthBits(X:Int) => 256 -Int #getMaskShiftBits(X:Int)             requires  0 <=Int #getMaskShiftBits(X) andBool 0 ==Int X >>Int #getMaskShiftBits(X) [concrete(X), simplification]
    rule [gmw-bits-succ-2]: #getMaskWidthBits(X:Int) => #getFirstOneBit(X >>Int #getMaskShiftBits(X)) requires  0 <=Int #getMaskShiftBits(X) andBool 0  <Int X >>Int #getMaskShiftBits(X) [concrete(X), simplification]
    rule [gmw-bits-fail]:   #getMaskWidthBits(X:Int) => -1                                            requires -1 ==Int #getMaskShiftBits(X) [concrete(X), simplification]

    rule [gmw-bytes-succ]: #getMaskWidthBytes(X:Int) => #getMaskWidthBits(X) /Int 8 requires           #getMaskWidthBits(X) modInt 8 ==Int 0   [concrete(X), simplification, preserves-definedness]
    rule [gmw-bytes-fail]: #getMaskWidthBytes(X:Int) => -1                          requires notBool ( #getMaskWidthBits(X) modInt 8 ==Int 0 ) [concrete(X), simplification, preserves-definedness]

    // Mask recogniser
    syntax Bool ::= #isMask(Int) [function, total]

    // A number is a mask if it has a valid shift, and a valid width, and all remaining bits set to one
    rule [is-mask-true]:
      #isMask(X:Int) => maxUInt256 ==Int X |Int ( 2 ^Int ( #getMaskShiftBits(X) +Int #getMaskWidthBits(X) ) -Int 1 )
        requires 0 <=Int #getMaskShiftBytes(X) andBool 0 <=Int #getMaskWidthBytes(X)
        [concrete(X), simplification, preserves-definedness]

    // and is not a mask otherwise
    rule [is-mask-false]:
      #isMask(X:Int) => false
        requires notBool ( 0 <=Int #getMaskShiftBytes(X) andBool 0 <=Int #getMaskWidthBytes(X) )
        [concrete(X), simplification, preserves-definedness]

    // ###########################################################################
    // Masking lemmas
    // ###########################################################################

    // Slot updates are of the general form (SHIFT *Int VALUE) |Int (MASK &Int #asWord( SLOT:Bytes )),
    // andthe masking clears the part of the slot into which VALUE will be stored,
    // and for VALUE to be stored correctly it first has to be shifted appropriately.
    // Note that SHIFT and MASK are always concrete.
    //
    // We perform this update in several stages:
    // 1. First, we simplify MASK &Int #asWord( SLOT ), which results in
    //    ( VALUE *Int SHIFT ) |Int #asWord ( B1 +Bytes ... +Bytes BN ).
    // 2. Then, we isolate the +Bytes-junct(s) that will be overwritten.
    // 3. Then, we write the VALUE, possibly splitting the identified +Bytes-junct(s).
    //
    // Note that we require additional simplifications to account for the fact that
    // VALUE and SLOT can also be concrete. In the former case, we need to extract the
    // SHIFT appropriate, and in the latter case, the slot will appear on the LHS of the |Int.

    // 1. Slot masking using &Int
    rule [mask-b-and]:
      MASK:Int &Int SLOT:Int =>
        #asWord ( #buf ( 32, SLOT ) [ 32 -Int ( #getMaskShiftBytes(MASK) +Int #getMaskWidthBytes(MASK) ) := #buf ( #getMaskWidthBytes(MASK), 0 ) ] )
        requires #rangeUInt(256, MASK) andBool #rangeUInt(256, SLOT)
        andBool #isMask(MASK)
        [simplification, concrete(MASK), preserves-definedness]

    // 2a. |Int and +Bytes, update to be done in left
    rule [bor-update-to-left]:
      A |Int #asWord ( B1 +Bytes B2 ) =>
        #asWord ( #buf ( 32 -Int lengthBytes(B2), (A /Int (2 ^Int (8 *Int lengthBytes(B2)))) |Int #asWord ( #buf (32 -Int (lengthBytes(B1) +Int lengthBytes(B2)), 0) +Bytes B1 ) ) +Bytes B2 )
        requires #rangeUInt(256, A) andBool A modInt (2 ^Int (8 *Int lengthBytes(B2))) ==Int 0 andBool lengthBytes(B1 +Bytes B2) <=Int 32
        [simplification, preserves-definedness]

    // 2b. |Int of +Bytes, update to be done in right
    rule [bor-update-to-right]:
      A |Int #asWord ( B1 +Bytes B2 ) =>
        #asWord ( B1 +Bytes #buf ( lengthBytes(B2), A |Int #asWord ( B2 ) ) )
        requires 0 <=Int A andBool A <Int 2 ^Int (8 *Int lengthBytes(B2))
        [simplification, preserves-definedness]

    // 3a. Update with explicit shift and symbolic slot
    rule [bor-update-with-shift]:
      ( SHIFT *Int X ) |Int Y => #asWord ( #buf( 32 -Int ( log2Int(SHIFT) /Int 8 ), X ) +Bytes #buf( log2Int(SHIFT) /Int 8, Y ) )
      requires rangeUInt(256, SHIFT) andBool SHIFT ==Int 2 ^Int log2Int(SHIFT) andBool log2Int(SHIFT) modInt 8 ==Int 0
       andBool 0 <=Int X andBool X <Int 2 ^Int (8 *Int (32 -Int ( log2Int(SHIFT) /Int 8 )))
       andBool 0 <=Int Y andBool Y <Int SHIFT
       [simplification, concrete(SHIFT), comm, preserves-definedness]

    // 3b. Buffer cropping
    rule [buf-asWord-crop]:
      #buf (W1:Int, #asWord(#buf(W2, X:Int) +Bytes B)) => #buf(W1 -Int lengthBytes(B), X) +Bytes B
      requires 0 <=Int W1 andBool 0 <=Int W2 andBool lengthBytes(B) <=Int W1 andBool W1 <=Int W2 +Int lengthBytes(B)
       andBool 0 <=Int X andBool X <Int 2 ^Int (8 *Int (W1 -Int lengthBytes(B)))
      [simplification]

    // 3c. Splitting the updated buffer into the updated value and the trailing zeros, explicit shift
    rule [buf-split-l]:
      #buf ( W, SHIFT *Int X ) => #buf( W -Int ( log2Int(SHIFT) /Int 8 ), X ) +Bytes #buf( log2Int(SHIFT) /Int 8, 0)
      requires 0 <=Int W andBool W <=Int 32 andBool rangeUInt(256, SHIFT)
       andBool SHIFT ==Int 2 ^Int log2Int(SHIFT)
       andBool log2Int(SHIFT) modInt 8 ==Int 0
       andBool 0 <=Int X andBool X <Int 2 ^Int (8 *Int (W -Int ( log2Int(SHIFT) /Int 8)))
       [simplification, concrete(W, SHIFT), preserves-definedness]

    // 3d. Splitting the updated buffer into the updated value and the trailing zeros, implicit shift
    rule [bor-split]:
      X |Int Y => #asWord ( #buf ( 32 -Int #getFirstOneBit(X) /Int 8, X /Int ( 2 ^Int ( 8 *Int ( #getFirstOneBit(X) /Int 8 ) ) ) ) +Bytes
                            #buf ( #getFirstOneBit(X) /Int 8, Y ) )
      requires #rangeUInt(256, X) andBool 0 <=Int #getFirstOneBit(X)
       andBool 0 <=Int Y andBool Y <Int 2 ^Int ( 8 *Int ( #getFirstOneBit(X) /Int 8 ) )
       [simplification, concrete(X), preserves-definedness]

    // 3e. Clearing update leftovers that only have bits higher than the buffer accepts
    rule [buf-bor-subsume]:
      #buf ( N, X |Int Y ) => #buf ( N, X )
      requires 0 <=Int N andBool N <=Int 32
       andBool 0 <=Int X andBool X <Int 2 ^Int ( 8 *Int N )
       andBool Y modInt 2 ^Int ( 8 *Int N ) ==Int 0
       [simplification, concrete(X), preserves-definedness]

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

    rule chop ( X -Int Y ) => X -Int Y
        requires #rangeUInt(256, X)
         andBool #rangeUInt(256, Y)
         andBool Y <=Int X
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

    rule bool2Word(B) *Int C <=Int A => notBool B orBool (B andBool C <=Int A)
      requires 0 <=Int A
      [simplification]

    rule bool2Word(X) *Int Y ==Int Z => (X andBool (Y ==Int Z)) orBool ((notBool X) andBool Z ==Int 0)
      [simplification]

    rule X *Int Y <=Int Z => Y <Int ( Z +Int 1 ) /Int X
      requires 0 <Int X andBool 0 <=Int Z andBool ( Z +Int 1) modInt X ==Int 0
      [simplification, concrete(X, Z), preserves-definedness]

endmodule
```