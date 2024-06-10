```k
requires "foundry.md"

module KONTROL-VM
    imports FOUNDRY

    syntax RPCRequest ::= ".RPCRequest"                 [symbol(EmptyRPCRequest)] 
                        | "#kontrol_requestValue"           [symbol(kontrol_requestValue)]
                        | "#eth_sendTransaction" TxType Int Int Int Int Int Int Bytes [symbol(eth_sendTransaction)]
                        | Int
    syntax KItem ::= "#eth_sendTransaction_final"

    syntax RPCResponse ::= ".RPCResponse" | String | Int | Bytes

    syntax Params ::= ".Params" | String | Int | Bytes
    
    configuration <simbolikVM>
                    <foundry/>
                    <rpcRequest> .RPCRequest </rpcRequest>
                    <rpcResponse> .RPCResponse </rpcResponse>
                    <params>
                      <p1> .Params </p1>
                      <p2> .Params </p2>
                      <p3> .Params </p3>
                      <p4> .Params </p4>
                      <p5> .Params </p5>
                      <p6> .Params </p6>
                    </params>
                  </simbolikVM>                       

    rule <k> #kontrol_requestValue => . ... </k> 
         <rpcResponse> _ => VALUE </rpcResponse>
         <p1> VALUE:Int </p1>

    rule <k> #eth_sendTransaction 
                TXTYPE
                ACCTFROM 
                ACCTTO 
                TXGAS 
                TXGASPRICE 
                TXVALUE 
                TXNONCE
                TXDATA =>
                .
              #loadTx 
                TXTYPE
                ACCTFROM 
                ACCTTO 
                TXGAS 
                TXGASPRICE 
                TXVALUE 
                TXNONCE
                TXDATA  
                 ~> #eth_sendTransaction_final 
                ... 
              </k>

    rule <k> #eth_sendTransaction_final => . ... </k> 
    
    syntax KItem ::= "#loadTx" TxType Int Int Int Int Int Int Bytes 
   // ---------------------------------------]
   // TODO: Replace the 0 with an index
    rule <k> #loadTx TXTYPE ACCTFROM ACCTTO TXGAS TXGASPRICE TXVALUE TXNONCE TXDATA
          => #makeTX 0
          ~> #loadNonce ACCTFROM 0
          ...
         </k>

    syntax EthereumCommand ::= "#makeTX" Int
   // ---------------------------------------
    rule <k> #makeTX TXID => . ... </k>
         <txOrder>   ... (.List => ListItem(TXID)) </txOrder>
         <txPending> ... (.List => ListItem(TXID)) </txPending>
         <gasPrice> GPRICE </gasPrice>
         <gasLimit> GLIMIT </gasLimit>
         <chainID> CID </chainID>
         <messages>
            ( .Bag
           => <message>
                <msgID>      TXID:Int </msgID>
                <txGasPrice> GPRICE   </txGasPrice>
                <txGasLimit> GLIMIT   </txGasLimit>
                <txChainID>  CID      </txChainID>
                ...
              </message>
            )
          ...
          </messages>

  syntax KItem ::= "#loadNonce" Int Int
  // -------------------------------------
    rule <k> #loadNonce ACCT TXID => . ... </k>
         <message>
           <msgID> TXID </msgID>
           <txNonce> _ => NONCE </txNonce>
           ...
         </message>
         <account>
           <acctID> ACCT </acctID>
           <nonce> NONCE </nonce>
           ...
         </account>

  syntax KItem ::= "loadTransaction" TxType Int Int Int Int Int Int Bytes
  
  //TODO: Retreive the proper value for txAccess cell 
  rule <k> loadTransaction  
                TXTYPE
                ACCTFROM 
                ACCTTO 
                TXGAS 
                TXGASPRICE 
                TXVALUE 
                TXNONCE
                TXDATA => . ... </k>
        <chainID> CID </chainID>
        <message> <msgID> TXID </msgID> <txNonce> _ => TXNONCE </txNonce> ... </message>
        <message> <msgID> TXID </msgID> <txGasPrice> _ => TXGASPRICE </txGasPrice> ... </message>
        <message> <msgID> TXID </msgID> <txGasLimit> _ => TXGAS </txGasLimit> ... </message>
        <message> <msgID> TXID </msgID> <to> _ => ACCTTO </to> ... </message>
        <message> <msgID> TXID </msgID> <value> _ => TXVALUE </value> ... </message>
        <message> <msgID> TXID </msgID> <data> _ => TXDATA </data> ... </message>
        <message> <msgID> TXID </msgID> <txType> _ => TXTYPE </txType> ... </message>
        <message> <msgID> TXID </msgID> <txChainID> _ => CID </txChainID> ... </message>
        <message> <msgID> TXID </msgID> <txAccess> _ => [ "null" ] </txAccess> ... </message>
        <rpcResponse> _ => 10 </rpcResponse>
endmodule

```