```k
module KONTROL-EVM-OPTIMIZATIONS
    imports EVM

    syntax Bool ::= #isValidJumpDest(Bytes, Int) [function, total]

    rule #isValidJumpDest(PGM, I) => PGM [ I ] ==Int 91 requires 0 <=Int I andBool I <Int lengthBytes(PGM)
    rule #isValidJumpDest(  _, _) => false              [owise]

    rule <k> JUMP DEST => #endBasicBlock... </k>
         <pc> _ => DEST </pc>
         <program> PGM </program>
      requires #isValidJumpDest(PGM, DEST)
      [priority(30)]

    rule <k> JUMP DEST => #end EVMC_BAD_JUMP_DESTINATION ... </k>
         <program> PGM </program>
      requires notBool #isValidJumpDest(PGM, DEST)
      [priority(30)]

endmodule
```