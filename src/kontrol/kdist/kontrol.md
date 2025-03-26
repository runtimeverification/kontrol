Kontrol Definitions
===================

This file defines the pre-built Kontrol definitions you get with a fresh install of Kontrol.
They include the base Foundry definition, and some optional lemmas (using command-line arguments to specify which ones to include).

```k
requires "foundry.md"
requires "no_stack_checks.md"
requires "no_code_size_checks.md"
requires "keccak.md"
requires "kontrol_lemmas.md"

module KONTROL-BASE
    imports FOUNDRY
    imports NO-STACK-CHECKS
    imports NO-CODE-SIZE-CHECKS
endmodule

module KONTROL-AUX
    imports KONTROL-BASE
    imports KONTROL-AUX-LEMMAS
endmodule

module KONTROL-KECCAK
    imports KONTROL-BASE
    imports KECCAK-LEMMAS
endmodule

module KONTROL-FULL
    imports KONTROL-AUX
    imports KONTROL-KECCAK
endmodule
```
