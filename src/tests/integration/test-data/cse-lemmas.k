requires "evm.md"
requires "foundry.md"

module CSE-LEMMAS
    imports BOOL
    imports FOUNDRY
    imports INFINITE-GAS
    imports INT-SYMBOLIC
    imports MAP-SYMBOLIC
    imports SET-SYMBOLIC

    // Non-equality of byte arrays
    rule { B1:Bytes #Equals B2:Bytes } => #Bottom
      requires notBool ( lengthBytes(B1) ==Int lengthBytes(B2) )
      [simplification]

endmodule

module CSE-LEMMAS-SPEC
    imports CSE-LEMMAS

endmodule