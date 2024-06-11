requires "evm.md"
requires "foundry.md"

module CSE-LEMMAS
    imports BOOL
    imports FOUNDRY
    imports INFINITE-GAS
    imports INT-SYMBOLIC
    imports MAP-SYMBOLIC
    imports SET-SYMBOLIC

    // xor in terms of -Int
    rule X xorInt maxUInt256 => maxUInt256 -Int X
      requires #rangeUInt ( 256 , X )
      [simplification]

    // for-loop chop
    rule chop ( ( X:Int +Int Y:Int ) ) ==Int 0 => X ==Int pow256 -Int (Y modInt pow256)
      requires #rangeUInt(256, X) andBool 0 <=Int Y
      [simplification, concrete(Y)]

    // Set equality needed for discharging `#Not ( #Exists ( ... )` on `<accessedAccounts>` unification
    rule { S1:Set #Equals S2:Set |Set SetItem ( X ) } =>
         { X in S1 } #And
         ( { S2 #Equals S1 } #Or { S2 #Equals S1 -Set SetItem ( X ) } )
         [simplification]

    // Non-equality of byte arrays
    rule { B1:Bytes #Equals B2:Bytes } => #Bottom
      requires notBool ( lengthBytes(B1) ==Int lengthBytes(B2) )
      [simplification]

    // Function selector does not match
    rule { B:Bytes #Equals B1:Bytes +Bytes _:Bytes } => #Bottom
      requires #range(B, 0, 4) =/=K #range (B1, 0, 4)
      [simplification(60), concrete(B, B1)]

    // Function selector matches
    rule { B:Bytes #Equals B1:Bytes +Bytes B2:Bytes } => {#range(B, 4, lengthBytes(B) -Int 4) #Equals B2}
      requires 4 <=Int lengthBytes(B) andBool #range(B, 0, 4) ==K B1
      [simplification(60), concrete(B, B1)]

    // Bitwise inequalities
    rule [bitwise-and-maxUInt-lt-l]:
      A <Int X &Int Y => false
      requires 0 <=Int X andBool 0 <=Int Y
       andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
       andBool X +Int 1 <=Int A
       [concrete(X), simplification, preserves-definedness]

    rule [bitwise-and-maxUInt-le-r]:
      X &Int Y <=Int A => true
      requires 0 <=Int X andBool 0 <=Int Y
       andBool X +Int 1 ==Int 2 ^Int log2Int(X +Int 1)
       andBool X +Int 1 <=Int A
       [concrete(X), simplification, preserves-definedness]

endmodule

module CSE-LEMMAS-SPEC
    imports CSE-LEMMAS

endmodule
