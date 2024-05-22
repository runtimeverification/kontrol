```k
requires "foundry.md"

module KONTROL-VM
    imports FOUNDRY

    

    syntax RPCRequest ::= ".RPCRequest" | Int 
    syntax RPCResponse ::= ".RPCResponse" | Int
    syntax KItem ::= "#kontrol_addAccount" | "#kontrol_addAccountByAddress" String | "#kontrol_addAccountByKey" String


    configuration <simbolikVM>
                    <foundry/>
                    <rpcRequest> .RPCRequest </rpcRequest>
                    <rpcResponse> .RPCResponse </rpcResponse>
                  </simbolikVM>

    
endmodule

```