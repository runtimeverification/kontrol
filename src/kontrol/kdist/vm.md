```k
requires "foundry.md"

module KONTROL-VM
    imports FOUNDRY

    syntax RPCRequest ::= ".RPCRequest"                 [symbol(EmptyRPCRequest)] 
                        | "#eth_requestValue"           [symbol(eth_requestValue)]
                        | "#eth_getBalance" String Int  [symbol(eth_getBalance)]
                        | Int
                           
    syntax RPCResponse ::= ".RPCResponse" | String | Int

    syntax KItem ::= "#kontrol_addAccount" | "#kontrol_addAccountByAddress" String | "#kontrol_addAccountByKey" String 

    configuration <simbolikVM>
                    <foundry/>
                    <rpcRequest> .RPCRequest </rpcRequest>
                    <rpcResponse> .RPCResponse </rpcResponse>
                  </simbolikVM>
    
    rule <k> #eth_requestValue => 3 </k> 
         <rpcResponse> _ => .RPCResponse </rpcResponse>

endmodule

```