Debug Collection with KEVM
--------------------------
This module handles the tracing of EVM opcodes during an execution.

```k
module EVM-TRACING
    imports EVM
```
The configuration of the KEVMTracing is defined as following:
- `<activeTracing>` signals if the tracing feature is active or not.
- `<traceStorage>` signals if the storage should be recorded in the `TraceItem`.
- `<traceWordStack>` signals if the storage should be recorded in the `TraceItem`.
- `<traceMemory>` signals if the storage should be recorded in the `TraceItem`.
- `<recordedTrace>` is an auxiliary cell that is used to determine if the current step has been recorded or not.
- `<traceData>` is a collection of `TraceItems`.

```k
    configuration
      <KEVMTracing>
        <activeTracing>  false </activeTracing>
        <traceStorage>   false </traceStorage>
        <traceWordStack> false </traceWordStack>
        <traceMemory>    false </traceMemory>
        <recordedTrace>  false </recordedTrace>
        <traceData>      .List </traceData>
      </KEVMTracing>
```
The `TraceItem` is a sort used to save information about the executed opcodes.
Each `TraceItem` contains:
- the current program counter
- the current opcode
- the storage of the contract that is being executed.
- the current word stack
- the current memory
- the current call depth

```k
    syntax TraceItem ::= "{" Int "|" OpCode "|" WordStack "|" Bytes "|" Map "|" Int "}"
 // -----------------------------------------------------------------------------------

    rule <k> #next [ OPC ] ... </k>
         <activeTracing>  true          </activeTracing>
         <traceStorage>   DSTG          </traceStorage>
         <traceWordStack> DSTK          </traceWordStack>
         <traceMemory>    DMEM          </traceMemory>
         <recordedTrace>  false => true </recordedTrace>
         <pc>             PCOUNT        </pc>
         <wordStack>      WS            </wordStack>
         <callDepth>      CD            </callDepth>
         <localMem>       MEM           </localMem>
         <id>             ACCT          </id>
         <account>
           <acctID>  ACCT    </acctID>
           <storage> STORAGE </storage>
           ...
         </account>
         <traceData>
           ...
           .List => ListItem({ PCOUNT
                             | OPC
                             | #if DSTK ==K true #then WS      #else .WordStack #fi
                             | #if DMEM ==K true #then MEM     #else .Bytes     #fi
                             | #if DSTG ==K true #then STORAGE #else .Map       #fi
                             | CD
                             })
         </traceData>
      [priority(25)]

    rule <k> #execute ... </k>
         <recordedTrace> true => false </recordedTrace>
      [priority(25)]

endmodule
 ```