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

endmodule

module CSE-LEMMAS-SPEC
    imports CSE-LEMMAS

endmodule