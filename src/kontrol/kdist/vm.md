```k
requires "foundry.md"
requires "state-utils.md"

module KONTROL-VM
    imports FOUNDRY
    imports STATE-UTILS

    syntax TxType ::= ".TxType"
                    | "Test"

    syntax RPCRequest ::= ".RPCRequest"                 [symbol(EmptyRPCRequest)] 
                        | "#kontrol_requestValue"           [symbol(kontrol_requestValue)]
                        | "#eth_sendTransaction" TxType Int Int Int Int Int Int Bytes [symbol(eth_sendTransaction)]
                        | Int

    syntax KItem ::= "#eth_sendTransaction_final"

    rule <k> TXID:Int ~> #eth_sendTransaction_final => . ... </k>
        //  <txPending> ListItem(TXID) => .List ... </txPending>
         <txOrder>   ListItem(TXID) => .List ... </txOrder>
         <currentTxID> TXID => TXID +Int 1 </currentTxID>
         <rpcResponse> _ => 200 </rpcResponse>

    syntax RPCResponse ::= ".RPCResponse" | String | Int | Bytes
    
    configuration <simbolikVM>
                    <foundry/>
                    <rpcRequest> .RPCRequest </rpcRequest>
                    <rpcResponse> .RPCResponse </rpcResponse>
                    <accountKeys> .Map </accountKeys>
                    <timeFreeze> true </timeFreeze>
                    <timeDiff> 0 </timeDiff>
                    <currentTxID> 0 </currentTxID>
                  </simbolikVM>                       

    rule <k> #kontrol_requestValue => . ... </k> 

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
                #startBlock 
                ~> #loadTx 
                  TXTYPE
                  ACCTFROM 
                  ACCTTO 
                  TXGAS 
                  TXGASPRICE 
                  TXVALUE 
                  TXNONCE
                  TXDATA  
                ~> #eth_sendTransaction_final 
                ~> #finalizeBlock
                ... 
              </k>
    
    syntax KItem ::= "#loadTx" TxType Int Int Int Int Int Int Bytes 
    // ---------------------------------------
    rule <k> #loadTx TXTYPE ACCTFROM ACCTTO TXGAS TXGASPRICE TXVALUE TXNONCE TXDATA
          => #makeTX TXID
          ~> #loadNonce ACCTFROM TXNONCE
          ~> #loadTransaction TXID TXTYPE ACCTFROM ACCTTO TXGAS TXGASPRICE TXVALUE TXNONCE TXDATA
          ~> #signTX TXID ACCTFROM
          ~> #prepareTx TXID ACCTFROM
          ~> TXID
          ...
         </k>
         <currentTxID> TXID </currentTxID>

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
          // <txAccess> _ => [ null:JSON ] </txAccess> 
          ...
        </message>

    syntax String ::= #unparseByteStack ( Bytes ) [function, klabel(unparseByteStack), symbol]
    rule #unparseByteStack(WS) => Bytes2String(WS)

    syntax String  ::=
        "Hex2Raw" "(" String ")" [function, klabel(Hex2Raw)]
      | "Raw2Hex" "(" String ")" [function, klabel(Raw2Hex)]

    rule Hex2Raw ( S ) => #unparseByteStack( #parseByteStack ( S ) )
  
    syntax KItem ::= "#signTX" Int Int
                   | "#signTX" Int String 
    // --------------------------------------------------------

    rule <k> #signTX TXID ACCTFROM:Int => #signTX TXID ECDSASign ( #hashTxData( #getTxData (TXID) ), #padToWidth( 32, #asByteStack( KEY ) ) )  ... </k>
        <accountKeys> ... ACCTFROM |-> KEY ... </accountKeys>
        <mode> NORMAL </mode>

    rule <k> #signTX TXID ACCTFROM:Int => #signTX TXID ECDSASign ( #hashTxData( #getTxData (TXID) ), #padToWidth( 32, #asByteStack( KEY ) ) )  ... </k>
        <accountKeys> ... ACCTFROM |-> KEY ... </accountKeys>
        <mode> NOGAS </mode>

    rule <k> #signTX TXID SIG:String => . ... </k>
         <message>
           <msgID> TXID </msgID>
           <sigR> _ => #parseHexBytes( substrString( SIG, 0, 64 ) )           </sigR>
           <sigS> _ => #parseHexBytes( substrString( SIG, 64, 128 ) )         </sigS>
           <sigV> _ => #parseHexWord( substrString( SIG, 128, 130 ) ) +Int 27 </sigV>
           ...
         </message>

    rule <k> #signTX TXID ACCTFROM:Int => . ... </k>
         <accountKeys> KEYMAP                      </accountKeys>
         <mode>        NORMAL                      </mode>
         <txPending>   ListItem(TXID) => .List ... </txPending>
         <txOrder>     ListItem(TXID) => .List ... </txOrder>
         <rpcResponse> _ => -1 </rpcResponse> // TODO: Come up with error code values for this cell
      requires notBool ACCTFROM in_keys(KEYMAP)

    syntax KItem ::= "#prepareTx" Int Account

    rule <k> #prepareTx TXID:Int ACCTFROM
          => #setup_G0 TXID 
          ~> #validateTx TXID 
          ~> #updateTimestamp
          ~> #executeTx TXID
          ... 
          </k>
         <origin> _ => ACCTFROM </origin>

    syntax KItem ::= "#setup_G0" Int
   // --------------------------------
    rule <k> #setup_G0 TXID => . ... </k>
         <schedule> SCHED </schedule>
         <callGas> _ => G0(SCHED, DATA, (ACCTTO ==K .Account) ) </callGas>
         <message>
           <msgID> TXID   </msgID>
           <data>  DATA   </data>
           <to>    ACCTTO </to>
           ...
         </message>

    syntax KItem ::= "#validateTx" Int
   // --------------------------------
    rule <k> #validateTx TXID => #end #if BAL <Int GLIMIT *Int GPRICE #then EVMC_BALANCE_UNDERFLOW #else EVMC_OUT_OF_GAS #fi ... </k>
         <callGas> G0_INIT </callGas>
         <origin> ACCTFROM </origin>
         <account>
           <acctID> ACCTFROM </acctID>
           <balance> BAL </balance>
           ...
         </account>
         <message>
           <msgID>      TXID   </msgID>
           <txGasPrice> GPRICE </txGasPrice>
           <txGasLimit> GLIMIT </txGasLimit>
           ...
         </message>
      requires GLIMIT <Int G0_INIT
        orBool BAL <Int GLIMIT *Int GPRICE
      

    rule <k> #validateTx TXID => . ... </k>
         <origin> ACCTFROM </origin>
         <callGas> G0_INIT => GLIMIT -Int G0_INIT </callGas>
         <account>
           <acctID> ACCTFROM </acctID>
           <balance> BAL </balance>
           ...
         </account>
         <message>
           <msgID>      TXID   </msgID>
           <txGasPrice> GPRICE </txGasPrice>
           <txGasLimit> GLIMIT </txGasLimit>
           ...
         </message>
      requires GLIMIT >=Int G0_INIT
       andBool BAL >=Int GLIMIT *Int GPRICE

    syntax KItem ::= "#updateTimestamp"
    // -----------------------------------
    rule <k> #updateTimestamp => . ... </k>
         <timestamp> _ => #time(TIMEFREEZE) +Int TIMEDIFF </timestamp>
         <timeFreeze> TIMEFREEZE </timeFreeze>
         <timeDiff>   TIMEDIFF   </timeDiff>

    syntax Int ::= #time( Bool ) [function]
    // ---------------------------------------
    rule #time(false) => 0 // TODO: Originally this was #time. Should represent the current time of the VM.
    rule #time(true)  => 0

    syntax EthereumCommand ::= "#finishTx"
    // ---------------------------------------
    rule <statusCode> _:ExceptionalStatusCode </statusCode> <k> #halt ~> #finishTx => #popCallStack ~> #popWorldState                   ... </k>
    rule <statusCode> EVMC_REVERT             </statusCode> <k> #halt ~> #finishTx => #popCallStack ~> #popWorldState ~> #refund GAVAIL ... </k> <gas> GAVAIL </gas>

    rule <statusCode> EVMC_SUCCESS </statusCode>
         <k> #halt ~> #finishTx => #mkCodeDeposit ACCT ... </k>
         <id> ACCT </id>
         <txPending> ListItem(TXID:Int) ... </txPending>
         <message>
           <msgID> TXID     </msgID>
           <to>    .Account </to>
           ...
         </message>

    rule <statusCode> EVMC_SUCCESS </statusCode>
         <k> #halt ~> #finishTx => #popCallStack ~> #dropWorldState ~> #refund GAVAIL ... </k>
         <gas> GAVAIL </gas>
         <txPending> ListItem(TXID:Int) ... </txPending>
         <message>
           <msgID> TXID </msgID>
           <to>    TT   </to>
           ...
         </message>
      requires TT =/=K .Account

    
    syntax EthereumCommand ::= #loadAccessList ( JSON )              [klabel(#loadAccessList)]
                             | #loadAccessListAux ( Account , List ) [klabel(#loadAccessListAux)]
 
    // ---------------------------------------------------------------------------------------------
    rule <k> #loadAccessList ([ .JSONs ]) => .K ... </k>
         <schedule> SCHED </schedule>
      requires Ghasaccesslist << SCHED >>

    rule <k> #loadAccessList ([ _ ]) => .K ... </k>
         <schedule> SCHED </schedule>
      requires notBool Ghasaccesslist << SCHED >>

    rule <k> #loadAccessList ([[ACCT, [STRG:JSONs]], REST])
          => #loadAccessListAux (#asAccount(ACCT), #parseAccessListStorageKeys([STRG]))
          ~> #loadAccessList ([REST])
         ...
         </k>
         <schedule> SCHED </schedule>
      requires Ghasaccesslist << SCHED >>

    rule <k> #loadAccessListAux (ACCT, (ListItem(STRGK) STRGKS))
          => #accessStorage ACCT STRGK:Int
          ~> #loadAccessListAux (ACCT, STRGKS)
         ...
         </k>
         <schedule> SCHED </schedule>
         <callGas> GLIMIT => GLIMIT -Int Gaccessliststoragekey < SCHED > </callGas>

    rule <k> #loadAccessListAux (ACCT, .List) => #accessAccounts ACCT ... </k>
         <schedule> SCHED </schedule>
         <callGas> GLIMIT => GLIMIT -Int Gaccesslistaddress < SCHED > </callGas>

    // ---------------------------------------------------------------------------------------------
  
    syntax KItem ::= "#executeTx" Int
   // ---------------------------------
    rule <k> #executeTx TXID:Int
          => #accessAccounts ACCTFROM #newAddr(ACCTFROM, NONCE) #precompiledAccountsSet(SCHED) 
          ~> #loadAccessList(TA)  
          ~> #create ACCTFROM #newAddr(ACCTFROM, NONCE) VALUE CODE 
          ~> #finishTx 
          ~> #finalizeTx(false)
         ...
         </k>
         <schedule> SCHED </schedule>
         <gasPrice> _ => GPRICE </gasPrice>
         <origin> ACCTFROM </origin>
         <callDepth> _ => -1 </callDepth>
         <txPending> ListItem(TXID:Int) ... </txPending>
         <message>
           <msgID>      TXID     </msgID>
           <txGasPrice> GPRICE   </txGasPrice>
           <txGasLimit> GLIMIT   </txGasLimit>
           <to>         .Account </to>
           <value>      VALUE    </value>
           <data>       CODE     </data>
           <txAccess>   TA       </txAccess>
           ...
         </message>
         <account>
           <acctID> ACCTFROM </acctID>
           <balance> BAL => BAL -Int (GLIMIT *Int GPRICE) </balance>
           <nonce> NONCE </nonce>
           ...
         </account>

    rule <k> #executeTx TXID:Int
          => #accessAccounts ACCTFROM ACCTTO #precompiledAccountsSet(SCHED)
          ~> #loadAccessList(TA)
          ~> #call ACCTFROM ACCTTO ACCTTO VALUE VALUE DATA false
          ~> #finishTx
          ~> #finalizeTx(false)
         ...
         </k>
         <schedule> SCHED </schedule>
         <origin> ACCTFROM </origin>
         <gasPrice> _ => GPRICE </gasPrice>
         <txPending> ListItem(TXID) ... </txPending>
         <callDepth> _ => -1 </callDepth>
         <message>
           <msgID>      TXID   </msgID>
           <txGasPrice> GPRICE </txGasPrice>
           <txGasLimit> GLIMIT </txGasLimit>
           <to>         ACCTTO </to>
           <value>      VALUE  </value>
           <data>       DATA   </data>
           <txAccess>   TA     </txAccess>
           ...
         </message>
         <account>
           <acctID> ACCTFROM </acctID>
           <balance> BAL => BAL -Int (GLIMIT *Int GPRICE) </balance>
           <nonce> NONCE => NONCE +Int 1 </nonce>
           ...
         </account>
      requires ACCTTO =/=K .Account

endmodule

```