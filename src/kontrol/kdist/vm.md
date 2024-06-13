```k
requires "foundry.md"

module KONTROL-VM
    imports FOUNDRY

    syntax TxType ::= ".TxType"
                    | "Test"

    syntax RPCRequest ::= ".RPCRequest"                 [symbol(EmptyRPCRequest)] 
                        | "#kontrol_requestValue"           [symbol(kontrol_requestValue)]
                        | "#eth_sendTransaction" TxType Int Int Int Int Int Int Bytes [symbol(eth_sendTransaction)]
                        | Int

    syntax RPCResponse ::= ".RPCResponse" | String | Int | Bytes
    
    configuration <simbolikVM>
                    <foundry/>
                    <rpcRequest> .RPCRequest </rpcRequest>
                    <rpcResponse> .RPCResponse </rpcResponse>
                    <accountKeys> .Map </accountKeys>
                  </simbolikVM>                       

    rule <k> #kontrol_requestValue => . ... </k> 
         <rpcResponse> _ => 10 </rpcResponse>

    syntax KItem ::= "#acctFromPrivateKey" String Int [symbol(acctFromPrivateKey)] 
    syntax KItem ::= "#setAcctBalance" Int Int 
    // ---------------------------------------------
    rule <k> #acctFromPrivateKey KEYSTR BAL => #newAccount #addrFromPrivateKey(KEYSTR) ~> #setAcctBalance #addrFromPrivateKey(KEYSTR) BAL ... </k>
         <accountKeys> M => M[#addrFromPrivateKey(KEYSTR) <- #parseHexWord(KEYSTR)] </accountKeys>
         
    rule <k> #setAcctBalance KEY BAL => . ... </k>
            <accounts> 
              <account>
                <acctID> KEY </acctID> 
                <balance> _ => BAL </balance> 
                ... 
              </account> 
              ... 
            </accounts> 

    rule <k> #eth_sendTransaction 
                TXTYPE
                ACCTFROM 
                ACCTTO 
                TXGAS 
                TXGASPRICE 
                TXVALUE 
                TXNONCE
                TXDATA
                 =>
              #loadTx 
                TXTYPE
                ACCTFROM 
                ACCTTO 
                TXGAS 
                TXGASPRICE 
                TXVALUE 
                TXNONCE
                TXDATA  
                ... 
              </k>
    
    syntax KItem ::= "#loadTx" TxType Int Int Int Int Int Int Bytes 
   // ---------------------------------------]
   // TODO: Replace the 0 with an index
    rule <k> #loadTx TXTYPE ACCTFROM ACCTTO TXGAS TXGASPRICE TXVALUE TXNONCE TXDATA
          => #makeTX 0
          ~> #loadNonce ACCTFROM TXNONCE
          ~> #loadTransaction 0 TXTYPE ACCTFROM ACCTTO TXGAS TXGASPRICE TXVALUE TXNONCE TXDATA
          ...
         </k>

    syntax EthereumCommand ::= "#makeTX" Int
   // ---------------------------------------
    // rule <k> #makeTX TXID => . ... </k>
    //      <message> <msgID> TXID:Int </msgID> ... </message>
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
          </messages> [owise, preserves-definedness]

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

  syntax KItem ::= "#loadTransaction" Int TxType Int Int Int Int Int Int Bytes
  
  //TODO: Retreive the proper value for txAccess cell 
  rule <k> #loadTransaction  
                TXID:Int
                TXTYPE:TxType
                ACCTFROM:Int 
                ACCTTO:Int 
                TXGAS:Int 
                TXGASPRICE:Int 
                TXVALUE:Int  
                TXNONCE:Int 
                TXDATA:Bytes => . ... </k>
        <chainID> CID </chainID>
        <message> 
          <msgID> TXID </msgID> 
          <txChainID> _ => CID </txChainID>
          <txNonce> _ => TXNONCE </txNonce> 
          <txGasPrice> _ => TXGASPRICE </txGasPrice> 
          <txGasLimit> _ => TXGAS </txGasLimit> 
          <to> _ => ACCTTO </to> 
          <value> _ => TXVALUE </value> 
          <data> _ => TXDATA </data> 
          <txType> _ => TXTYPE </txType> 
          <txAccess> _ => [ "null" ] </txAccess> 
          ...
        </message>
        <rpcResponse> _ => 10 </rpcResponse>


  
    // syntax KItem ::= "signTX" Int Int
    //                | "signTX" Int String 
    // // --------------------------------------------------------
    // rule <k> signTX TXID ACCTFROM:Int => signTX TXID ECDSASign( Hex2Raw ( #hashUnsignedTx(TXTYPE, TN, TP, TG, TT, TV, TD, CID, TA ) ), #unparseByteStack( #padToWidth( 32, #asByteStack( KEY ) ) ) ) ... </k>
    //      <accountKeys> ... ACCTFROM |-> KEY ... </accountKeys>
    //      <mode> NORMAL </mode>
    //      <message>
    //        <msgID> TXID </msgID>
    //        <txNonce>    TN     </txNonce>
    //        <txGasPrice> TP     </txGasPrice>
    //        <txGasLimit> TG     </txGasLimit>
    //        <to>         TT     </to>
    //        <value>      TV     </value>
    //        <data>       TD     </data>
    //        <txType>     TXTYPE </txType>
    //        <txAccess>   TA     </txAccess>
    //        <txChainID>  CID    </txChainID>
    //        ...
    //      </message>

    // rule <k> signTX TXID ACCTFROM:Int => signTX TXID ECDSASign( Hex2Raw( #hashUnsignedTx(TXTYPE, TN, TP, TG, TT, TV, TD, CID, TA) ), #unparseByteStack( ( #padToWidth( 20, #asByteStack( ACCTFROM ) ) ++ #padToWidth( 20, #asByteStack( ACCTFROM ) ) )[0 .. 32] ) ) ... </k>
    //      <mode> NOGAS </mode>
    //      <message>
    //        <msgID> TXID </msgID>
    //        <txNonce>    TN     </txNonce>
    //        <txGasPrice> TP     </txGasPrice>
    //        <txGasLimit> TG     </txGasLimit>
    //        <to>         TT     </to>
    //        <value>      TV     </value>
    //        <data>       TD     </data>
    //        <txType>     TXTYPE </txType>
    //        <txAccess>   TA     </txAccess>
    //        <txChainID>  CID    </txChainID>
    //        ...
    //      </message>

    // rule <k> signTX TXID SIG:String => . ... </k>
    //      <message>
    //        <msgID> TXID </msgID>
    //        <sigR> _ => #parseHexBytes( substrString( SIG, 0, 64 ) )           </sigR>
    //        <sigS> _ => #parseHexBytes( substrString( SIG, 64, 128 ) )         </sigS>
    //        <sigV> _ => #parseHexWord( substrString( SIG, 128, 130 ) ) +Int 27 </sigV>
    //        ...
    //      </message>

    // rule <k> signTX TXID ACCTFROM:Int => . ... </k>
    //      <accountKeys> KEYMAP                      </accountKeys>
    //      <mode>        NORMAL                      </mode>
    //      <txPending>   ListItem(TXID) => .List ... </txPending>
    //      <txOrder>     ListItem(TXID) => .List ... </txOrder>
    //     <rpcResponse> _ => 11 </rpcResponse>
    //   requires notBool ACCTFROM in_keys(KEYMAP)

endmodule

```