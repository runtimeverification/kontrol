```k

module KONTROL-VM
    imports INT
    imports BOOL
    imports STRING

    syntax RPCRequest ::= ".RPCRequest" | Int 
    syntax RPCResponse ::= ".RPCResponse" | Int
    syntax KItem ::= "#kontrol_addAccount" | "#kontrol_addAccountByAddress" String | "#kontrol_addAccountByKey" String
                    

    rule <k> #kontrol_addAccount => . ... </k> 

endmodule

```