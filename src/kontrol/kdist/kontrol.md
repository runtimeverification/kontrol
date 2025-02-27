Kontrol Definitions
===================

This file defines the pre-built Kontrol definitions you get with a fresh install of Kontrol.
They include the base Foundry definition, and some optional lemmas (using command-line arguments to specify which ones to include).

```k
requires "foundry.md"
requires "no_stack_checks.md"
requires "no_code_size_checks.md"

module KONTROL-BASE
    imports FOUNDRY
    imports NO-STACK-CHECKS
    imports NO-CODE-SIZE-CHECKS
endmodule
```
