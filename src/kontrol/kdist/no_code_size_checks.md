Relaxed Bytecode Limits Rules
===================

The provided rule disables the enforcement of the code size limit introduced in EIP-170 during contract deployment.
That enables the deployment of larger test contracts containing auxiliary functions for verification and testing.
In addition, it enhances compatibility with Foundry, which also does not enforce the code size limit.

```k
requires "foundry.md"

module NO-CODE-SIZE-CHECKS
    imports EVM
    imports FOUNDRY

    rule <k> #mkCodeDeposit ACCT
          => Gcodedeposit < SCHED > *Int lengthBytes(OUT) ~> #deductGas
          ~> #finishCodeDeposit ACCT OUT
         ...
         </k>
         <schedule> SCHED </schedule>
         <output> OUT => .Bytes </output>
      requires #isValidCode(OUT, SCHED)
   [priority(30)]

endmodule
```