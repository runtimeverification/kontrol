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

    rule (A ~> B) ==K (C ~> B) => (A ==K C) [simplification]

    // Function selector comparison
    rule { B:Bytes #Equals B1:Bytes +Bytes B2:Bytes } => #Bottom
      requires #range(B, 0, 4) =/=K #range (B1, 0, 4)
      [simplification(60), concrete(B, B1)]

    // Function selector comparison
    rule { B:Bytes #Equals B1:Bytes +Bytes B2:Bytes } => {#range(B, 4, lengthBytes(B) -Int 4) #Equals B2}
      requires #range(B, 0, 4) ==K B1
      [simplification(60), concrete(B, B1)]

    rule { M1:Map ( K:Int |-> V:Int ) #Equals M2:Map [ K <- V ] } => { M1 #Equals (M2 [ K <- undef]) }
    [simplification(60)]

    rule { ( K:Int |-> V:Int ) #Equals M2:Map [ K <- V ] } => { .Map #Equals (M2 [ K <- undef]) }
    [simplification(60)]

    rule M:Map [ K:Int <- V:Int ] => ( K |-> V ) requires .Map ==K M [ K <- undef ] [simplification(60)]

    rule { .Map #Equals M:Map [ K:Int <- undef ] } => ({M #Equals .Map} #Or {M #Equals (K |-> #lookup(M, K))})
    [simplification]


//     // Function selector comparison
//     rule { B:Bytes #Equals B1:Bytes +Bytes B2:Bytes } => { #range(B, minInt(lengthBytes(B), lengthBytes(B1)), lengthBytes(B)) #Equals B2 }
//       requires #range(B, 0, minInt(lengthBytes(B), lengthBytes(B1))) =/=K #range (B1, 0, minInt(lengthBytes(B), lengthBytes(B1)))
//       [simplification(60), concrete(B, B1)]


endmodule

module CSE-LEMMAS-SPEC
    imports CSE-LEMMAS

endmodule
