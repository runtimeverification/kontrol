Kontrol Cheat Codes
-------------------
This file contains the implementation of both Foundry and proprietary cheat codes supported by Kontrol.

The configuration of the Foundry Cheat Codes is defined as follwing:
1. The `<prank>` subconfiguration stores values which are used during the execution of any kind of `prank` cheat code:
    - `<prevCaller>` keeps the current address of the contract that initiated the prank.
    - `<prevOrigin>` keeps the current address of the `tx.origin` value.
    - `<newCaller>` and `<newOrigin>` are addresses to be assigned after the prank call to `msg.sender` and `tx.origin`.
    - `<active>` signals if a prank is active or not.
    - `<depth>` records the current call depth at which the prank was invoked.
    - `<singleCall>` tells whether the prank stops by itself after the next call or when a `stopPrank` cheat code is invoked.
2. The `<expectedRevert>` subconfiguration stores values used for the `expectRevert` cheat code.
    - `<isRevertExpected>` flags if the next call is expected to revert or not.
    - `<expectedDepth>` records the depth at which the call is expected to revert.
    - `<expectedReason>` keeps the expected revert message as a `Bytes`.
3. The `<expectOpcode>` subconfiguration stores values used for `expect*OPCODE*` cheat codes.
    - `<isOpcodeExpected>` flags if a call opcode is expected.
    - `<expectedAddress>` keeps the expected caller.
    - `<expectedValue>` keeps expected `msg.value`.
    - `<expectedData>` keeps expected `calldata`.
    - `<opcodeType>` keeps track of what `CALL*` Opcode is expected.
4. The `<expectEmit>` subconfiguration stores values used for the `expectEmit` cheat code.
    - `<recordEvent>` flags if the next emitted Event should be recorded and held for future matches.
    - `<isEventExpected>` flags if an Event is expected to match the one recorded previously.
    - `<checkedTopics>` will store a list of `bool` values that flag if a topic should be checked or not.
    - `<checkedData>` flags if the data field should be checked or not.
    - `<expectedEventAddress>` stores the emitter of an expected Event.
5. The `<whitelist>` subconfiguration stores addresses that can be called and storage slots that can be accessed/modified during the execution.
    - `<isCallWhitelistActive>` flags if the whitelist mode is enabled for calls.
    - `<isStorageWhitelistActive>` flags if the whitelist mode is enabled for storage changes.
    - `<addressSet>` - stores the address whitelist.
    - `<storageSlotSet>` - stores the storage whitelist containing pairs of addresses and storage indexes.
6. The `<mockCalls>` subconfiguration stores information about mock calls that are active.
    - `<mockCall>`- collection that stores which mock calls are active for each address.
      - `<mockAddress>` - address which has one or more active mock calls.
      - `<mockValues>` - map from a mock call calldata (key) and its respective returndata.
```k
requires "abi.md"

module FOUNDRY-CHEAT-CODES
    imports EVM
    imports EVM-ABI
    imports FOUNDRY-ACCOUNTS
    imports INFINITE-GAS

    configuration
      <cheatcodes>
        <prank>
          <prevCaller> .Account </prevCaller>
          <prevOrigin> .Account </prevOrigin>
          <newCaller> .Account </newCaller>
          <newOrigin> .Account </newOrigin>
          <active> false </active>
          <depth> 0 </depth>
          <singleCall> false </singleCall>
        </prank>
        <expectedRevert>
          <isRevertExpected> false </isRevertExpected>
          <expectedReason> .Bytes </expectedReason>
          <expectedDepth> 0 </expectedDepth>
        </expectedRevert>
        <expectedOpcode>
          <isOpcodeExpected> false </isOpcodeExpected>
          <expectedAddress> .Account </expectedAddress>
          <expectedValue> 0 </expectedValue>
          <expectedData> .Bytes </expectedData>
          <opcodeType> .OpcodeType </opcodeType>
        </expectedOpcode>
        <expectEmit>
          <recordEvent> false </recordEvent>
          <isEventExpected> false </isEventExpected>
          <checkedTopics> .List </checkedTopics>
          <checkedData> false </checkedData>
          <expectedEventAddress> .Account </expectedEventAddress>
        </expectEmit>
        <whitelist>
          <isCallWhitelistActive> false </isCallWhitelistActive>
          <isStorageWhitelistActive> false </isStorageWhitelistActive>
          <addressSet> .Set </addressSet>
          <storageSlotSet> .Set </storageSlotSet>
        </whitelist>
        <mockCalls>
            <mockCall multiplicity="*" type="Map">
               <mockAddress> .Account </mockAddress>
               <mockValues>  .Map </mockValues>
            </mockCall>
         </mockCalls>
      </cheatcodes>
```

Below, we define rules for the `#cheatcode_call` production, handling the cheat codes.

#### `assume` - Insert a condition

```
function assume(bool) external;
```

`cheatcode.call.assume` will match when the `assume` cheat code function is called.
This rule then takes a `bool` condition from the function call data, represented using the `ARGS` variable, and injects it into the execution path using the `#assume` production.
`==K #bufStrict(32, 1)` is used to mark that the condition should hold.

```k
    rule [cheatcode.call.assume]:
         <k> #cheatcode_call SELECTOR ARGS => #assume(ARGS ==K #bufStrict(32, 1)) ... </k>
      requires SELECTOR ==Int selector ( "assume(bool)" )
      [preserves-definedness]
```

#### `deal` - Set a given balance to a given account.

```
function deal(address who, uint256 newBalance) external;
```

`cheatcode.call.deal` will match when the `deal` cheat code function is called.
The rule then takes from the function call data the target account, using `#asWord(#range(ARGS, 0, 32)`, and the new balance, using `#asWord(#range(ARGS, 32, 32))`, and forwards them to the `#setBalance` production which updates the account accordingly.

```k
    rule [cheatcode.call.deal]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(#range(ARGS, 0, 32)) ~> #setBalance #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ( "deal(address,uint256)" )
```

#### `etch` - Sets the code of an account.

```
function etch(address who, bytes calldata code) external;
```

`cheatcode.call.etch` will match when the `etch` cheat code function is called.
This rule then takes from the function call data the target account, using `#asWord(#range(ARGS, 0, 32)`, and the new bytecode, using `#range(ARGS, CODE_START, CODE_LENGTH)`, where `#asWord(#range(ARGS, 64, 32))` is used to determine the length of the second argument.
The values are forwarded to the `#setCode` production which updates the account accordingly.

```k
    rule [cheatcode.call.etch]:
         <k> #cheatcode_call SELECTOR ARGS
          => #loadAccount #asWord(#range(ARGS, 0, 32))
          ~> #setCode #asWord(#range(ARGS, 0, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32)))
         ...
         </k>
      requires SELECTOR ==Int selector ( "etch(address,bytes)" )
```

#### `warp` - Sets the block timestamp.

```
function warp(uint256) external;
```

`cheatcode.call.warp` will match when the `warp` cheat code function is called.
This rule then takes the `uint256` value from the function call data which is represented as `ARGS` and updates the `<timestamp>` cell.

```k
    rule [cheatcode.call.warp]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <timestamp> _ => #asWord(ARGS) </timestamp>
      requires SELECTOR ==Int selector( "warp(uint256)" )
```

#### `roll` - Sets the block number.

```
function roll(uint256) external;
```

`cheatcode.call.roll` will match when the `roll` cheat code function is called.
This rule then takes the `uint256` value from the function call data which is represented as `ARGS` and updates the `<number>` cell.

```k
    rule [cheatcode.call.roll]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <number> _ => #asWord(ARGS) </number>
      requires SELECTOR ==Int selector ( "roll(uint256)" )
```

#### `fee` - Sets the block base fee.

```
function fee(uint256) external;
```

`cheatcode.call.fee` will match when the `fee` cheat code function is called.
This rule then takes the `uint256` value from the function call data which is represented as `ARGS` and updates the `<baseFee>` cell.

```k
    rule [cheatcode.call.fee]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <baseFee> _ => #asWord(ARGS) </baseFee>
      requires SELECTOR ==Int selector ( "fee(uint256)" )
```

#### `chainId` - Sets the chain ID.

```
function chainId(uint256) external;
```

`cheatcode.call.chainId` will match when the `chainId` cheat code function is called.
This rule then takes the `uint256` value from the function call data which is represented as `ARGS` and updates the `<chainID>` cell.

```k
    rule [cheatcode.call.chainId]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <chainID> _ => #asWord(ARGS) </chainID>
      requires SELECTOR ==Int selector ( "chainId(uint256)" )
```

#### `coinbase` - Sets the block coinbase.

```
function coinbase(address) external;
```

`cheatcode.call.coinbase` will match when the `coinbase` cheat code function is called.
This rule then takes the `uint256` value from the function call data which is represented as `ARGS` and updates the `<coinbase>` cell.

```k
    rule [cheatcode.call.coinbase]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <coinbase> _ => #asWord(ARGS) </coinbase>
      requires SELECTOR ==Int selector ( "coinbase(address)" )
```

#### `label` - Sets a label for a given address.

```
function label(address addr, string calldata label) external;
```

`cheatcode.call.label` will match when the `label` cheat code function is called.
If an address is labelled, the label will show up in test traces instead of the address.
However, there is no change on the state and therefore this rule just skips the cheatcode invocation.

```k
    rule [cheatcode.call.label]:
         <k> #cheatcode_call SELECTOR _ARGS => .K ... </k>
      requires SELECTOR ==Int selector ( "label(address,string)" )
```

#### `getNonce` - Gets the nonce of the given account.

```
function getNonce(address account) external returns (uint64);
```

`cheatcode.call.getNonce` will match when the `getNonce` cheat code function is called.
This rule takes the `address` value from the function call data, which is represented as `ARGS`, and forwards it to the `#returnNonce` production, which will update the `<output>` cell with the `nonce` of the account.

```k
    rule [cheatcode.call.getNonce]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(ARGS) ~> #returnNonce #asWord(ARGS) ... </k>
      requires SELECTOR ==Int selector ( "getNonce(address)" )
```

#### `setNonce` - Sets the nonce of the given account.

```
function setNonce(address account, uint64 nonce) external;
```

`cheatcode.call.setNonce` will match when the `setNonce` function is called.
This rule takes the `address` value and `uint64` value corresponding to new nonce using from the function call data, which is represented as `ARGS` forwards it to the `#setNonce` production, which will update the nonce of the account.

```k
    rule [cheatcode.call.setNonce]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(#range(ARGS, 0, 32)) ~> #setNonce #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ( "setNonce(address,uint64)" )
```

#### `addr` - Computes the address for a given private key.

```
function addr(uint256 privateKey) external returns (address);
```

`cheatcode.call.addr` will match when the `addr` cheat code function is called.
This rule takes `uint256` private key from the function call data, which is represented as `ARGS`, and computes the address.
The `<output>` cell will be updated with the value of the address generated from the private key, padded to 32 bytes wide.

```k
    rule [cheatcode.call.addr]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <output> _ => #bufStrict(32, #addrFromPrivateKey(#unparseDataBytes(ARGS))) </output>
      requires SELECTOR ==Int selector ( "addr(uint256)" )
      [preserves-definedness]
```

#### `load` - Loads a storage slot from an address.

```
function load(address account, bytes32 slot) external returns (bytes32);
```

`cheatcode.call.load` will match when the `load` cheat code function is called.
This rule loads the storage slot identified by `#asWord(#range(ARGS, 32, 32))` (referring to `slot` argument) from account `#asWord(#range(ARGS, 0, 32))` (referring to `account`).
The value of the identified storage slot is placed in the `<output>` cell using the `#returnStorage` production.

```k
    rule [cheatcode.call.load]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(#range(ARGS, 0, 32)) ~> #returnStorage #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) ... </k>
      requires SELECTOR ==Int selector ( "load(address,bytes32)" )
```

#### `store` - Stores a value to an address' storage slot.

```
function store(address account, bytes32 slot, bytes32 value) external;
```

`cheatcode.call.store` will match when the `store` cheat code function is called.
This rule then takes from the function call data the account using `#asWord(#range(ARGS, 0, 32))` and the new slot value using `#asWord(#range(ARGS, 32, 32))` and updates the slot denoted by `#asWord(#range(ARGS, 64, 32))`.

```k
    rule [cheatcode.call.store]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(#range(ARGS, 0, 32)) ~> #setStorage #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) #asWord(#range(ARGS, 64, 32)) ... </k>
      requires SELECTOR ==Int selector ( "store(address,bytes32,bytes32)" )
```

#### `symbolicStorage` - Makes the storage of the given address completely symbolic.

```
function symbolicStorage(address) external;
```

`cheatcode.call.symbolicStorage` will match when the `symbolicStorage` cheat code function is called.
This rule then takes the address using `#asWord(#range(ARGS, 0, 32))` and makes its storage completely symbolic.

```k
    rule [cheatcode.call.symbolicStorage]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(ARGS) ~> #setSymbolicStorage #asWord(ARGS) ... </k>
      requires SELECTOR ==Int selector ( "symbolicStorage(address)" )
```

#### `freshUInt` - Returns a single symbolic unsigned integer.

```
function freshUInt(uint8) external returns (uint256);
```

`cheatcode.call.freshUInt` will match when the `freshUInt` cheat code function is called.
This rule returns a symbolic integer of up to the bit width that was sent as an argument.

```{.k .symbolic}
    rule [cheatcode.call.freshUInt]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <output> _ => #buf(32, ?WORD) </output>
      requires SELECTOR ==Int selector ( "freshUInt(uint8)" )
       andBool 0 <Int #asWord(ARGS) andBool #asWord(ARGS) <=Int 32
       ensures 0 <=Int ?WORD andBool ?WORD <Int 2 ^Int (8 *Int #asWord(ARGS))
       [preserves-definedness]
```

#### `freshBool` - Returns a single symbolic boolean.

```
function freshBool() external returns (bool);
```

`cheatcode.call.freshBool` will match when the `freshBool` cheat code function is called.
This rule returns a symbolic boolean value being either 0 (false) or 1 (true).

```{.k .symbolic}
    rule [cheatcode.call.freshBool]:
         <k> #cheatcode_call SELECTOR _ => .K ... </k>
         <output> _ => #buf(32, ?WORD) </output>
      requires SELECTOR ==Int selector ( "freshBool()" )
       ensures #rangeBool(?WORD)
       [preserves-definedness]
```

#### `freshBytes` - Returns a single symbolic boolean.

```
function freshBytes(uint256) external returns (bytes memory);
```

`cheatcode.call.freshBytes` will match when the `freshBytes` cheat code function is called.
This rule returns a fully symbolic byte array value of the given length.

```{.k .symbolic}
    rule [cheatcode.call.freshBytes]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <output> _ =>
            #buf(32, 32) +Bytes #buf(32, #asWord(ARGS)) +Bytes ?BYTES
            +Bytes #buf ( ( ( notMaxUInt5 &Int ( #asWord(ARGS) +Int maxUInt5 ) ) -Int #asWord(ARGS) ) , 0 )
         </output>
      requires SELECTOR ==Int selector ( "freshBytes(uint256)" )
      ensures lengthBytes(?BYTES) ==Int #asWord(ARGS)
      [preserves-definedness]
```

Expecting the next call to revert
---------------------------------

```
function expectRevert() external;
function expectRevert(bytes4 msg) external;
function expectRevert(bytes calldata msg) external;
```

All cheat code calls which take place while `expectRevert` is active are ignored.

```k
    rule [cheatcode.call.ignoreCalls]:
         <k> #cheatcode_call _ _ => .K ... </k>
         <expectedRevert>
           <isRevertExpected> true </isRevertExpected>
           ...
         </expectedRevert>
      [priority(35)]
```

We use the `#next[OP]` to identify OpCodes that can revert and insert a `#checkRevert` production used to examine the end of each call/create in KEVM.
The check will be inserted only if the current depth is the same as the depth at which the `expectRevert` cheat code was used.
WThe `#checkRevert` will be used to compare the status code of the execution and the output of the call against the expect reason provided.

```k
    rule [foundry.set.expectrevert.1]:
         <k> #next [ _OP:CallOp ] ~> (.K => #checkRevert ~> #updateRevertOutput RETSTART RETWIDTH) ~> #execute ... </k>
         <callDepth> CD </callDepth>
         <wordStack> _ : _ : _ : _ : _ : RETSTART : RETWIDTH : _WS </wordStack>
         <expectedRevert>
           <isRevertExpected> true </isRevertExpected>
           <expectedDepth> CD </expectedDepth>
           ...
         </expectedRevert>
      [priority(38)]

    rule [foundry.set.expectrevert.2]:
         <k> #next [ _OP:CallSixOp ] ~> (.K => #checkRevert ~> #updateRevertOutput RETSTART RETWIDTH) ~> #execute ... </k>
         <callDepth> CD </callDepth>
         <wordStack> _ : _ : _ : _ : RETSTART : RETWIDTH : _WS </wordStack>
         <expectedRevert>
           <isRevertExpected> true </isRevertExpected>
           <expectedDepth> CD </expectedDepth>
           ...
         </expectedRevert>
      [priority(38)]

    rule [foundry.set.expectrevert.3]:
         <k> #next [ OP:OpCode ] ~> (.K => #checkRevert) ~> #execute ... </k>
         <callDepth> CD </callDepth>
         <expectedRevert>
           <isRevertExpected> true </isRevertExpected>
           <expectedDepth> CD </expectedDepth>
           ...
         </expectedRevert>
      requires (OP ==K CREATE orBool OP ==K CREATE2)
      [priority(38)]
```

If the `expectRevert()` selector is matched, call the `#setExpectRevert` production to initialize the `<expectedRevert>` subconfiguration.

```k
    rule [cheatcode.call.expectRevert]:
         <k> #cheatcode_call SELECTOR ARGS => #setExpectRevert ARGS ... </k>
      requires SELECTOR ==Int selector ( "expectRevert()" )
        orBool SELECTOR ==Int selector ( "expectRevert(bytes)" )
```

Expecting a specific CALL/CREATE opcode
---------------------------------------

First we define a sort to identify expected opcodes.

```k
    syntax OpcodeType ::= ".OpcodeType" | "Call" | "Static" | "Delegate" | "Create" | "Create2"
```

If the `expect*OPCODE*` selector is matched, the rule will load the account into the state and add the `#setExpectOpcode` production to the K cell to initialize the `<expectedOpcode/>` subconfiguration with the given parameters.

```k
    rule [cheatcode.call.expectStaticCall]:
         <k> #cheatcode_call SELECTOR ARGS
          => #loadAccount #asWord(#range(ARGS, 0, 32))
          ~> #setExpectOpcode #asWord(#range(ARGS, 0, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32))) 0 Static
          ...
         </k>
      requires SELECTOR ==Int selector ( "expectStaticCall(address,bytes)" )

    rule [cheatcode.call.expectDelegateCall]:
         <k> #cheatcode_call SELECTOR ARGS
          => #loadAccount #asWord(#range(ARGS, 0, 32))
          ~> #setExpectOpcode #asWord(#range(ARGS, 0, 32)) #range(ARGS, 96, #asWord(#range(ARGS, 64, 32))) 0 Delegate
          ...
         </k>
      requires SELECTOR ==Int selector ( "expectDelegateCall(address,bytes)" )

    rule [cheatcode.call.expectRegularCall]:
         <k> #cheatcode_call SELECTOR ARGS
          => #loadAccount #asWord(#range(ARGS, 0, 32))
          ~> #setExpectOpcode #asWord(#range(ARGS, 0, 32)) #range(ARGS, 128, #asWord(#range(ARGS, 96, 32))) #asWord(#range(ARGS, 32, 32)) Call
          ...
         </k>
      requires SELECTOR ==Int selector ( "expectRegularCall(address,uint256,bytes)" )

    rule [cheatcode.call.expectCreate]:
         <k> #cheatcode_call SELECTOR ARGS
          => #loadAccount #asWord(#range(ARGS, 0, 32))
          ~> #setExpectOpcode #asWord(#range(ARGS, 0, 32)) #range(ARGS, 128, #asWord(#range(ARGS, 96, 32))) #asWord(#range(ARGS, 32, 32)) Create
          ...
         </k>
      requires SELECTOR ==Int selector ( "expectCreate(address,uint256,bytes)" )

    rule [cheatcode.call.expectCreate2]:
         <k> #cheatcode_call SELECTOR ARGS
          => #loadAccount #asWord(#range(ARGS, 0, 32))
          ~> #setExpectOpcode #asWord(#range(ARGS, 0, 32)) #range(ARGS, 128, #asWord(#range(ARGS, 96, 32))) #asWord(#range(ARGS, 32, 32)) Create2
          ...
         </k>
      requires SELECTOR ==Int selector ( "expectCreate2(address,uint256,bytes)" )
```

Next, everytime one of the `STATICCALL`, `DELEGATECALL`, `CALL`, `CREATE` or `CREATE2` opcodes is executed, we check if the `sender` address, `msg.value` and `calldata` match the expected values.
`calldata` needs to match only the first byte.

```k
    rule <k> (.K => #clearExpectOpcode) ~> STATICCALL _GCAP ACCTTO ARGSTART ARGWIDTH _RETSTART _RETWIDTH ... </k>
         <localMem> LM </localMem>
         <expectedOpcode>
           <isOpcodeExpected> true </isOpcodeExpected>
           <expectedAddress> ACCTTO </expectedAddress>
           <expectedData> DATA </expectedData>
           <opcodeType> Static </opcodeType>
           ...
         </expectedOpcode>
      requires #range(LM, ARGSTART, ARGWIDTH) ==K #range(DATA, 0, ARGWIDTH)
      [priority(40)]

    rule <k> (.K => #clearExpectOpcode) ~> DELEGATECALL _GCAP ACCTTO ARGSTART ARGWIDTH _RETSTART _RETWIDTH ... </k>
         <localMem> LM </localMem>
         <expectedOpcode>
           <isOpcodeExpected> true </isOpcodeExpected>
           <expectedAddress> ACCTTO </expectedAddress>
           <expectedData> DATA </expectedData>
           <opcodeType> Delegate </opcodeType>
           ...
         </expectedOpcode>
      requires #range(LM, ARGSTART, ARGWIDTH) ==K #range(DATA, 0, ARGWIDTH)
      [priority(40)]

    rule <k> (.K => #clearExpectOpcode) ~> CALL _GCAP ACCTTO VALUE ARGSTART ARGWIDTH _RETSTART _RETWIDTH ... </k>
         <localMem> LM </localMem>
         <expectedOpcode>
           <isOpcodeExpected> true </isOpcodeExpected>
           <expectedAddress> ACCTTO </expectedAddress>
           <expectedData> DATA </expectedData>
           <opcodeType> Call </opcodeType>
           <expectedValue> VALUE </expectedValue>
         </expectedOpcode>
      requires #range(LM, ARGSTART, ARGWIDTH) ==K #range(DATA, 0, ARGWIDTH)
      [priority(40)]

    rule <k> (.K => #clearExpectOpcode) ~> CREATE VALUE MEMSTART MEMWIDTH ... </k>
         <localMem> LM </localMem>
         <id> ACCT </id>
         <expectedOpcode>
           <isOpcodeExpected> true </isOpcodeExpected>
           <expectedAddress> ACCT </expectedAddress>
           <expectedData> DATA </expectedData>
           <opcodeType> Create </opcodeType>
           <expectedValue> VALUE </expectedValue>
         </expectedOpcode>
      requires #range(LM, MEMSTART, MEMWIDTH) ==K #range(DATA, 0, MEMWIDTH)
      [priority(40)]

    rule <k> (.K => #clearExpectOpcode) ~> CREATE2 VALUE MEMSTART MEMWIDTH _SALT ... </k>
         <localMem> LM </localMem>
         <id> ACCT </id>
         <expectedOpcode>
           <isOpcodeExpected> true </isOpcodeExpected>
           <expectedAddress> ACCT </expectedAddress>
           <expectedData> DATA </expectedData>
           <opcodeType> Create2 </opcodeType>
           <expectedValue> VALUE </expectedValue>
         </expectedOpcode>
      requires #range(LM, MEMSTART, MEMWIDTH) ==K #range(DATA, 0, MEMWIDTH)
      [priority(40)]
```

Pranks
------

#### Injecting addresses in a call

To inject the pranked `msg.sender` and `tx.origin` we use the `#next[OP:Opcode]` to identify when the next opcode `OP` is either `CALL`, `CALLCODE`, `STATICCALL`, `CREATE` or `CREATE2`.
The `foundry.prank` rule will match only if:
   - `<active>` cell has the `true` value, signaling that a prank is active,
   - the call that's being made is not a cheat code invocation,
   - the current depth of the call is at the same level with the depth at which the prank was invoked.
The last point is required in order to prevent overwriting the caller for subcalls.
`#injectPrank` and `#endPrank` are the productions that will update the address values for `msg.sender` and `tx.origin`.

```k
    rule [foundry.prank]:
         <k> #next [ OP:OpCode ] => #injectPrank ~> #next [ OP:OpCode ] ~> #endPrank ... </k>
         <callDepth> CD </callDepth>
         <wordStack> _ : ACCTTO : _WS </wordStack>
         <id> ACCT </id>
         <prank>
           <active> true </active>
           <newCaller> NCL </newCaller>
           <depth> CD </depth>
           ...
         </prank>
      requires ACCT =/=K NCL
       andBool ACCTTO =/=K #address(FoundryCheat)
       andBool (OP ==K CALL orBool OP ==K CALLCODE orBool OP ==K STATICCALL orBool OP ==K CREATE orBool OP ==K CREATE2)
      [priority(40)]
```

#### `startPrank` - Sets `msg.sender` and `tx.origin` for all subsequent calls until `stopPrank` is called.

```
function startPrank(address) external;
function startPrank(address sender, address origin) external;
```

`cheatcode.call.startPrank` and `cheatcode.call.startPrankWithOrigin` will match when either of `startPrank` functions are called.
The addresses which will be used to impersonate future calls are retrieved from the local memory using `#asWord(#range(ARGS, 0, 32)` for the sender, and `#asWord(#range(ARGS, 32, 32)` for the origin (only for the `cheatcode.call.startPrankWithOrigin` rule).
The `#loadAccount` production is used to load accounts into the state if they are missing.

```k
    rule [cheatcode.call.startPrank]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(ARGS) ~> #setPrank #asWord(ARGS) .Account false ... </k>
      requires SELECTOR ==Int selector ( "startPrank(address)" )

    rule [cheatcode.call.startPrankWithOrigin]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(#range(ARGS, 0, 32)) ~> #loadAccount #asWord(#range(ARGS, 32, 32)) ~> #setPrank #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) false ... </k>
      requires SELECTOR ==Int selector ( "startPrank(address,address)" )
```

#### `prank` - Impersonate `msg.sender` and `tx.origin` for only for the next call.

```
function prank(address) external;
function prank(address sender, address origin) external;
```

```k
    rule [cheatcode.call.prank]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(ARGS) ~> #setPrank #asWord(ARGS) .Account true ... </k>
      requires SELECTOR ==Int selector ( "prank(address)" )

    rule [cheatcode.call.prankWithOrigin]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(#range(ARGS, 0, 32)) ~> #loadAccount #asWord(#range(ARGS, 32, 32)) ~> #setPrank #asWord(#range(ARGS, 0, 32)) #asWord(#range(ARGS, 32, 32)) true ... </k>
      requires SELECTOR ==Int selector ( "prank(address,address)" )
```

#### `stopPrank` - Stops impersonating `msg.sender` and `tx.origin`.

```
function stopPrank() external;
```

`cheatcode.call.stopPrank` will match when `stopPrank` function will be called. This rule will invoke `#endPrank` which will clean up the `<prank/>` subconfiguration and restore the previous values of the `msg.sender` and `tx.origin`.

```k
    rule [cheatcode.call.stopPrank]:
         <k> #cheatcode_call SELECTOR _ => #endPrank ~> #clearPrank ... </k>
      requires SELECTOR ==Int selector ( "stopPrank()" )
```

Gas Manipulation
----------------

### `setGas` - Sets the current gas left (reported by `GAS` opcode) to a specific amount.

```
function setGas(uint256 newGas) external;
```

`setGas` is useful when writing tests that depend on the gas used, and so a specific concrete amount is needed instead of the default infinite gas.

```{.k .bytes}
    rule [cheatcode.call.setGas]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <gas> _ => #asWord(ARGS) </gas>
         <callGas> _ => 0 </callGas>
      requires SELECTOR ==Int selector ( "setGas(uint256)" )
```

### `infiniteGas` - Sets the remaining gas to an infinite value.

```
function infiniteGas() external;
```

`infiniteGas` is useful for running tests without them running out of gas.
It is applied by default.

```{.k .bytes .symbolic}
    rule [cheatcode.call.infiniteGas]:
         <k> #cheatcode_call SELECTOR _ARGS => .K ... </k>
         <gas> _ => #gas(?_VGAS) </gas>
         <callGas> _ => #gas(?_VCALLGAS) </callGas>
      requires SELECTOR ==Int selector ( "infiniteGas()" )
```

Expecting Events
----------------
```
function expectEmit(bool checkTopic1, bool checkTopic2, bool checkTopic3, bool checkData) external;
function expectEmit(bool checkTopic1, bool checkTopic2, bool checkTopic3, bool checkData, address emitter) external;
```

Assert a specific log is emitted before the end of the current function.

Call the cheat code, specifying whether we should check the first, second or third topic, and the log data.
Topic 0 is always checked.
Emit the event we are supposed to see before the end of the current function.
Perform the call.
If the event is not available in the current scope (e.g. if we are using an interface, or an external smart contract), we can define the event ourselves with an identical event signature.

There are 2 signatures:

Without checking the emitter address: Asserts the topics match without checking the emitting address.
With address: Asserts the topics match and that the emitting address matches.

```k
    rule [cheatcode.call.expectEmit]:
         <k> #cheatcode_call SELECTOR ARGS => #setExpectEmit word2Bool(#asWord(#range(ARGS, 0, 32))) word2Bool(#asWord(#range(ARGS, 32, 32))) word2Bool(#asWord(#range(ARGS, 64, 32))) word2Bool(#asWord(#range(ARGS, 96, 32))) .Account ... </k>
      requires SELECTOR ==Int selector ( "expectEmit(bool,bool,bool,bool)" )

    rule [cheatcode.call.expectEmitAddr]:
         <k> #cheatcode_call SELECTOR ARGS => #setExpectEmit word2Bool(#asWord(#range(ARGS, 0, 32))) word2Bool(#asWord(#range(ARGS, 32, 32))) word2Bool(#asWord(#range(ARGS, 64, 32))) word2Bool(#asWord(#range(ARGS, 96, 32))) #asWord(#range(ARGS, 128, 32)) ... </k>
      requires SELECTOR ==Int selector ( "expectEmit(bool,bool,bool,bool,address)" )
```

The `foundry.recordExpectedEvent` is used to record the event that is emitted following the `expectEmit` cheat code.
When the `LOG(N)` OpCode is executed, a new `SubstateLogItem` will be stored in the `<log>` cell, including the `N` topics that are fetched from the `<wordStack>`.
This rule incorporates the logic of the [evm-semantics `LOG` opcode rule](https://github.com/runtimeverification/evm-semantics/blob/v1.0.489/kevm-pyk/src/kevm_pyk/kproj/evm-semantics/evm.md?plain=1#L1132-L1137).
Any change to the rule in evm-semantics needs to be included here as well.

```k
    rule [foundry.recordExpectedEvent]:
         <k> LOG(N) MEMSTART MEMWIDTH => .K ... </k>
         <expectEmit>
          <recordEvent> true => false </recordEvent>
          <isEventExpected> false => true </isEventExpected>
          ...
        </expectEmit>
         <id> ACCT </id>
         <wordStack> WS => #drop(N, WS) </wordStack>
         <localMem> LM </localMem>
         <log> L => L ListItem({ ACCT | WordStack2List(#take(N, WS)) | #range(LM, MEMSTART, MEMWIDTH) }) </log>
      requires #sizeWordStack(WS) >=Int N
      [priority(40)]
```

`foundry.compareEvents` is used to compare the expected event with the one that is currently being emitted.
If the events match, the `expectEmit` cheat code is marked as successful using `#clearExpectEmit`.
Regardless if the events match or not, the canon `LOG(N)` [rule from evm-semantics](https://github.com/runtimeverification/evm-semantics/blob/v1.0.489/kevm-pyk/src/kevm_pyk/kproj/evm-semantics/evm.md?plain=1#L1132-L1137) will store the new event in the `<log>` cell.

```k
    rule [foundry.compareEvents]:
         <k> (.K => #clearExpectEmit ) ~> LOG(N) MEMSTART MEMWIDTH ... </k>
         <log> _ ListItem({ _ | TOPICS | DATA }:SubstateLogEntry) </log>
         <id> ACCT </id>
         <expectEmit>
          <recordEvent> false </recordEvent>
          <isEventExpected> true </isEventExpected>
          <checkedTopics> CHECKS </checkedTopics>
          <checkedData> CHECKDATA </checkedData>
          <expectedEventAddress> ADDR </expectedEventAddress>
        </expectEmit>
        <wordStack> WS </wordStack>
        <localMem> LM </localMem>
      requires #sizeWordStack(WS) >=Int N
       andBool  #checkTopics(CHECKS, TOPICS, WordStack2List(#take(N, WS)))
       andBool ((notBool CHECKDATA) orBool (#asWord(DATA) ==Int #asWord(#range(LM, MEMSTART, MEMWIDTH))))
       andBool (ADDR ==K .Account orBool ADDR ==K ACCT)
      [priority(40)]
```


Restricting the accounts that can be called in Kontrol
------------------------------------------------------

A `StorageSlot` pair is formed from an address and a storage index.

```k
    syntax StorageSlot ::= "{" Int "|" Int "}"
 // ------------------------------------------
```

We define two new status codes:
 - `KONTROL_WHITELISTCALL`, which signals that an address outside the whitelist has been called during the execution.
 - `KONTROL_WHITELISTSTORAGE`, which signals that a storage index of an address outside the whitelist has been changed during the execution.

```k
    syntax ExceptionalStatusCode ::= "KONTROL_WHITELISTCALL"
                                   | "KONTROL_WHITELISTSTORAGE"
 // -----------------------------------------------------------
```


The `ACCTTO` value is checked for each call while the whitelist restriction is enabled for calls.
If the address is not in the whitelist `WLIST` then `KEVM` goes into an error state providing the `ACCTTO` value.

```k
    rule [foundry.catchNonWhitelistedCalls]:
         <k> (#call _ ACCTTO _ _ _ _ false
          ~> #popCallStack
          ~> #popWorldState) => #end KONTROL_WHITELISTCALL ... </k>
         <whitelist>
           <isCallWhitelistActive> true </isCallWhitelistActive>
           <addressSet> WLIST </addressSet>
           ...
         </whitelist>
      requires notBool ACCTTO in WLIST
      [priority(40)]
```

When the storage whitelist restriction is enabled, the `SSTORE` operation will check if the address and the storage index are in the whitelist.
If the pair is not present in the whitelist `WLIST` then `KEVM` goes into an error state providing the address and the storage index values.

```k
    rule [foundry.catchNonWhitelistedStorageChanges]:
         <k> SSTORE INDEX _ => #end KONTROL_WHITELISTSTORAGE ... </k>
         <id> ACCT </id>
         <statusCode> _ => KONTROL_WHITELISTSTORAGE </statusCode>
         <whitelist>
           <isStorageWhitelistActive> true </isStorageWhitelistActive>
           <storageSlotSet> WLIST </storageSlotSet>
           ...
         </whitelist>
      requires notBool {ACCT|INDEX} in WLIST
      [priority(40)]
```

#### `allowCallsToAddress` - Add an account address to a whitelist.

```
function allowCallsToAddress(address) external;
```

Adds an account address to the whitelist. The execution of the modified KEVM will stop when a call has been made to an address which is not in the whitelist.

```k
    rule [foundry.allowCallsToAddress]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(ARGS) ~> #addAddressToWhitelist #asWord(ARGS) ... </k>
         requires SELECTOR ==Int selector ( "allowCallsToAddress(address)" )
```

#### `allowChangesToStorage` - Add an account address and a storage slot to a whitelist.

```
function allowChangesToStorage(address,uint256) external;
```

```k
    rule [foundry.allowStorageSlotToAddress]:
         <k> #cheatcode_call SELECTOR ARGS => #loadAccount #asWord(ARGS) ~> #addStorageSlotToWhitelist { #asWord(#range(ARGS, 0, 32)) | #asWord(#range(ARGS, 32, 32)) } ... </k>
         requires SELECTOR ==Int selector ( "allowChangesToStorage(address,uint256)" )
```


#### `sign` - Signs a digest with private key

```
function sign(uint256 privateKey, bytes32 digest) external returns (uint8 v, bytes32 r, bytes32 s);
```

`cheatcode.call.sign` will match when the `sign` cheat code function is called.
This rule takes the `privateKey` to sign using `#range(ARGS,0,32)` and the `digest` to be signed using `#range(ARGS, 32, 32)`,
then performs the signature by passing them to the `ECDSASign ( Bytes, Bytes )` function (from KEVM).
The `ECDSASign` function returns the signed data in [r,s,v] form, which we convert to a `Bytes` using `#parseByteStack`.

```k
    rule [cheatcode.call.sign]:
         <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
         <output> _ => #sign(#range(ARGS, 32, 32),#range(ARGS,0,32)) </output>
      requires SELECTOR ==Int selector ( "sign(uint256,bytes32)" )
      [preserves-definedness]
```

Otherwise, throw an error for any other call to the Foundry contract.

```k
    rule [cheatcode.call.owise]:
         <k> #cheatcode_call SELECTOR ARGS => #cheatcode_error SELECTOR ARGS ... </k>
         <statusCode> _ => CHEATCODE_UNIMPLEMENTED </statusCode>
      [owise]
```

Mock calls
----------

#### `mockCall` - Mocks all calls to an address where if the call data either strictly or loosely matches data and returns retdata.

```
function mockCall(address where, bytes calldata data, bytes calldata retdata) external;
```

`cheatcode.call.mockCall` will match when the `mockCall` cheat code function is called.
This rule then takes the `address` value from the function calldata and etches a single byte into the account code, in case it is empty.
The rule also takes the bytes `CALLDATA` and the bytes `RETURNDATA` from the function calldata and forwards them, together with the address to be mocked, to the `setMockCall` production.
The `setMockCall` production will update the configuration in order to store the information of the mock call.

The current implementation of the `mockCall` cheatcode has some limitations:
- It does not work if there are multiple mock calls with common prefixes for the same address - see test `MockCallTestFoundry.testMockCallMultiplePartialMatch`

```k
    rule [cheatcode.call.mockCall]:
         <k> #cheatcode_call SELECTOR ARGS
          => #loadAccount #asWord(#range(ARGS, 0, 32))
          ~> #etchAccountIfEmpty #asWord(#range(ARGS, 0, 32))
          ~> #setMockCall #asWord(#range(ARGS, 0, 32)) #range(ARGS, #asWord(#range(ARGS, 32, 32)) +Int 32, #asWord(#range(ARGS, #asWord(#range(ARGS, 32, 32)), 32))) #range(ARGS, #asWord(#range(ARGS, 64, 32)) +Int 32, #asWord(#range(ARGS, #asWord(#range(ARGS, 64, 32)), 32)))
         ...
         </k> 
      requires SELECTOR ==Int selector ( "mockCall(address,bytes,bytes)" )
```

We use `#next[OP]` to identify OpCodes that represent function calls. If there is `<mockCall>`, for which `<mockAddress>` matches the `ACCTTO` and `<mockValues>` has a key `CALLDATA` that matches some prefix of the function calldata, then the `#execMockCall` will replace the function execution and update the output with the `RETURNDATA`.

```k
    rule [foundry.set.mockCall]:
         <k> #next [ OP:CallOp ] => #execMockCall RETSTART RETWIDTH RETURNDATA ~> #pc [ OP ] ... </k>
         <localMem> LM </localMem>
         <wordStack> _ : ACCTTO : _ : ARGSTART : _ : RETSTART : RETWIDTH : WS => WS </wordStack>
         <mockCall>
           <mockAddress> ACCTTO </mockAddress>
           <mockValues>...  CALLDATA |-> RETURNDATA ...</mockValues>
         </mockCall>
         requires #range(LM, ARGSTART, lengthBytes(CALLDATA)) ==K CALLDATA
      [priority(30)]

    rule [foundry.set.mockCall2]:
         <k> #next [ OP:CallSixOp ] => #execMockCall RETSTART RETWIDTH RETURNDATA ~> #pc [ OP ] ... </k>
         <localMem> LM </localMem>
         <wordStack> _ : ACCTTO : ARGSTART : _ : RETSTART : RETWIDTH : WS => WS </wordStack>
         <mockCall>
           <mockAddress> ACCTTO </mockAddress>
           <mockValues>...  CALLDATA |-> RETURNDATA ...</mockValues>
         </mockCall>
         requires #range(LM, ARGSTART, lengthBytes(CALLDATA)) ==K CALLDATA
      [priority(30)]
```

Utils
-----

- `#loadAccount ACCT` creates a new, empty account for `ACCT` if it does not already exist. Otherwise, it has no effect.

```k
    syntax KItem ::= "#loadAccount" Int [klabel(foundry_loadAccount)]
 // -----------------------------------------------------------------
    rule <k> #loadAccount ACCT => #accessAccounts ACCT ... </k> <account> <acctID> ACCT </acctID> ... </account>
    rule <k> #loadAccount ACCT => #newAccount ACCT ~> #accessAccounts ACCT ... </k> [owise]
```

- `#setBalance ACCTID NEWBAL` sets the balance of a given account.

```k
    syntax KItem ::= "#setBalance" Int Int [klabel(foundry_setBalance)]
 // -------------------------------------------------------------------
    rule <k> #setBalance ACCTID NEWBAL => .K ... </k>
         <account>
           <acctID> ACCTID </acctID>
           <balance> _ => NEWBAL </balance>
           ...
         </account>
```

- `#setCode ACCTID CODE` sets the code of a given account.

```k
    syntax KItem ::= "#setCode" Int Bytes [klabel(foundry_setCode)]
 // ---------------------------------------------------------------
    rule <k> #setCode ACCTID CODE => .K ... </k>
         <account>
           <acctID> ACCTID </acctID>
           <code> _ => #if #asWord(CODE) ==Int 0 #then .Bytes #else CODE #fi </code>
           ...
         </account>
```

- `#returnNonce ACCTID` takes the nonce of a given account and places it on the `<output>` cell.

```k
    syntax KItem ::= "#returnNonce" Int [klabel(foundry_returnNonce)]
 // -----------------------------------------------------------------
    rule <k> #returnNonce ACCTID => .K ... </k>
         <output> _ => #bufStrict(32, NONCE) </output>
         <account>
           <acctID> ACCTID </acctID>
           <nonce> NONCE </nonce>
           ...
         </account>
```

- `#setNonce ACCTID NONCE` takes a given account and a given nonce and update the account accordingly.

```k
     syntax KItem ::= "#setNonce" Int Int [klabel(foundry_setNonce)]
 // ----------------------------------------------------------------
    rule <k> #setNonce ACCTID NONCE => .K ... </k>
         <account>
             <acctID> ACCTID </acctID>
             <nonce> _ => NONCE </nonce>
             ...
         </account>
```

- `#returnStorage ACCTID LOC` takes a storage value from a given account and places it on the `<output>` cell.

```k
    syntax KItem ::= "#returnStorage" Int Int [klabel(foundry_returnStorage)]
 // -------------------------------------------------------------------------
    rule <k> #returnStorage ACCTID LOC => .K ... </k>
         <output> _ => #bufStrict(32, #lookup(STORAGE, LOC)) </output>
         <account>
           <acctID> ACCTID </acctID>
           <storage> STORAGE </storage>
           ...
         </account>
```

- `#setStorage ACCTID LOC VALUE` sets a given value to a given location of an account.

```k
    syntax KItem ::= "#setStorage" Int Int Int [klabel(foundry_setStorage)]
 // -----------------------------------------------------------------------
    rule <k> #setStorage ACCTID LOC VALUE => .K ... </k>
         <account>
           <acctID> ACCTID </acctID>
           <storage> STORAGE => STORAGE [ LOC <- VALUE ] </storage>
             ...
         </account>
```

`#setSymbolicStorage ACCTID` takes a given account and makes its storage fully symbolic.

```k
     syntax KItem ::= "#setSymbolicStorage" Int [klabel(foundry_setSymbolicStorage)]
```

```{.k .symbolic}
    rule <k> #setSymbolicStorage ACCTID => .K ... </k>
         <account>
           <acctID> ACCTID </acctID>
           <storage> _ => ?STORAGE </storage>
           <origStorage> _ => ?STORAGE </origStorage>
           ...
         </account>
```

- `#setExpectRevert` sets the `<expectedRevert>` subconfiguration with the current call depth and the expected message from `expectRevert`.

```k
    syntax KItem ::= "#setExpectRevert" Bytes [klabel(foundry_setExpectRevert)]
 // ---------------------------------------------------------------------------
    rule <k> #setExpectRevert EXPECTED => .K ... </k>
         <callDepth> CD </callDepth>
         <expectedRevert>
           <isRevertExpected> false => true </isRevertExpected>
           <expectedDepth> _ => CD </expectedDepth>
           <expectedReason> _ => EXPECTED </expectedReason>
         </expectedRevert>
```

- `#clearExpectRevert` sets the `<expectedRevert>` subconfiguration to initial values.

```k
    syntax KItem ::= "#clearExpectRevert" [klabel(foundry_clearExpectRevert)]
 // -------------------------------------------------------------------------
    rule <k> #clearExpectRevert => .K ... </k>
         <expectedRevert>
           <isRevertExpected> _ => false </isRevertExpected>
           <expectedDepth> _ => 0 </expectedDepth>
           <expectedReason> _ => .Bytes </expectedReason>
         </expectedRevert>
```

- `#updateRevertOutput` if a call reverted as expected, resets the local memory at position `START` and width `WIDTH` with the modified output from `#checkRevert`.
Otherwise, the output is already in the local memory, so `#setLocalMem` does not change anything.

```k
    syntax KItem ::= "#updateRevertOutput" Int Int [klabel("foundry_updateRevertOutput")]
 // -------------------------------------------------------------------------------------
    rule <k> #updateRevertOutput START WIDTH => #setLocalMem START WIDTH OUT ... </k> <output> OUT </output>
```

- `#checkRevert` is used to check if a `CALL`/`CREATE` opcode reverted as expected.
If the status code is not `EVMC_SUCCESS` and `#matchReason` confirms that the output `OUT` matches the expected reason `REASON`, then we change the status code to `EVMC_SUCCESS` and update the output of the operation to remove the error message.
Otherwise, if the status code is `EVMC_SUCCESS`, or the output does not match the reason, then it means that the operation did not revert as expected and `expectRevert` fails accordingly.
`#clearExpectRevert` is used to end the `expectRevert` cheat code.

```k
    syntax KItem ::= "#checkRevert" [klabel("foundry_checkRevert")]
 // ---------------------------------------------------------------
    rule <k> #checkRevert => #clearExpectRevert ... </k>
         <statusCode> SC => EVMC_SUCCESS </statusCode>
         <wordStack> 0 : WS => 1 : WS </wordStack>
         <output> OUT => #buf (512, 0) </output>
         <callDepth> CD </callDepth>
         <expectedRevert>
           <isRevertExpected> true </isRevertExpected>
           <expectedDepth> CD </expectedDepth>
           <expectedReason> REASON </expectedReason>
         </expectedRevert>
      requires SC =/=K EVMC_SUCCESS
       andBool #matchReason(REASON, #encodeOutput(OUT))

    rule <k> #checkRevert => #markAsFailed ~> #clearExpectRevert ... </k>
         <statusCode> SC </statusCode>
         <output> OUT </output>
         <callDepth> CD </callDepth>
         <expectedRevert>
           <isRevertExpected> true </isRevertExpected>
           <expectedDepth> CD </expectedDepth>
           <expectedReason> REASON </expectedReason>
         </expectedRevert>
      requires SC =/=K EVMC_SUCCESS
       andBool notBool #matchReason(REASON, #encodeOutput(OUT))

    rule <k> #checkRevert => #markAsFailed ~> #clearExpectRevert ... </k>
         <statusCode> EVMC_SUCCESS => EVMC_REVERT </statusCode>
         <wordStack> 1 : WS => 0 : WS </wordStack>
         <callDepth> CD </callDepth>
         <expectedRevert>
           <isRevertExpected> true </isRevertExpected>
           <expectedDepth> CD </expectedDepth>
           ...
         </expectedRevert>

    rule <k> #checkRevert => .K ... </k>
         <expectedRevert>
           <isRevertExpected> false </isRevertExpected>
           ...
         </expectedRevert>
```

- `#encodeOutput` - will encode the output `Bytes` to match the encoding of the `Bytes` in `<expectedReason>` cell.
    - If the `revert` instruction and the `expectRevert` cheat code are used with a custom error, then `expectRevert` will store the message with the encoding `abi.encode(abi.encodeWithSelector(CustomError.selector, 1, 2))`, while the output cell will contain only the `abi.encodeWithSelector(CustomError.selector, 1, 2)`.
    - If the `revert` instruction and the `expectRevert` cheat code are used with a string, then `expectRevert` will store the only the encoded string, while the `<output>` cell will store the encoded built-in error `Error(string)`.
    Since the encoding `abi.encode(abi.encodeWithSelector(Error.selector, 1, 2))` cannot be easily decoded when symbolic variables are used, the `<output>` Bytes object is encoded again when the default `Error(string)` is not used.

```k
    syntax Bytes ::= "#encodeOutput" "(" Bytes ")" [function, total, klabel(foundry_encodeOutput)]
 // ----------------------------------------------------------------------------------------------
    rule #encodeOutput(BA) => #abiCallData("expectRevert", #bytes(BA)) requires notBool #range(BA, 0, 4) ==K Int2Bytes(4, selector("Error(string)"), BE)
    rule #encodeOutput(BA) => BA [owise]
```

- `#matchReason(REASON,OUT)` will check if the returned message matches the expected reason of the revert.
Will also return true if REASON is `.Bytes`.

```k
    syntax Bool ::= "#matchReason" "(" Bytes "," Bytes ")" [function, klabel(foundry_matchReason)]
 // ----------------------------------------------------------------------------------------------
    rule #matchReason(REASON, _) => true requires REASON ==K .Bytes
    rule #matchReason(REASON, OUT) => REASON ==K #range(OUT, 4, lengthBytes(OUT) -Int 4) requires REASON =/=K .Bytes
```

- `#setExpectOpcode` initializes the `<expectedOpcode>` subconfiguration with an expected `Address`, and `Bytes` to match the calldata.
`CallType` is used to specify what `CALL*` opcode is expected.

```k
    syntax KItem ::= "#setExpectOpcode" Account Bytes Int OpcodeType [klabel(foundry_setExpectOpcode)]
 // --------------------------------------------------------------------------------------------------
    rule <k> #setExpectOpcode ACCT DATA VALUE OPTYPE => .K ... </k>
         <expectedOpcode>
           <isOpcodeExpected> _ => true </isOpcodeExpected>
           <expectedAddress> _ => ACCT </expectedAddress>
           <expectedData> _ => DATA </expectedData>
           <expectedValue> _ => VALUE </expectedValue>
           <opcodeType> _ => OPTYPE </opcodeType>
         </expectedOpcode>
```

- `#clearExpectOpcode` restore the `<expectedOpcode>` subconfiguration to its initial values.

```k
    syntax KItem ::= "#clearExpectOpcode" [klabel(foundry_clearExpectOpcode)]
 // -------------------------------------------------------------------------
    rule <k> #clearExpectOpcode => .K ... </k>
         <expectedOpcode>
           <isOpcodeExpected> _ => false </isOpcodeExpected>
           <expectedAddress> _ => .Account </expectedAddress>
           <expectedData> _ => .Bytes </expectedData>
           <opcodeType> _ => .OpcodeType </opcodeType>
           <expectedValue> _ => 0 </expectedValue>
         </expectedOpcode>
```

- `#setPrank NEWCALLER NEWORIGIN SINGLEPRANK` will set the `<prank/>` subconfiguration for the given accounts.

```k
    syntax KItem ::= "#setPrank" Int Account Bool [klabel(foundry_setPrank)]
 // ------------------------------------------------------------------------
    rule <k> #setPrank NEWCALLER NEWORIGIN SINGLEPRANK => .K ... </k>
         <callDepth> CD </callDepth>
         <id> CL </id>
         <origin> OG </origin>
         <prank>
           <prevCaller> _ => CL </prevCaller>
           <prevOrigin> _ => OG </prevOrigin>
           <newCaller> _ => NEWCALLER </newCaller>
           <newOrigin> _ => NEWORIGIN </newOrigin>
           <active> false => true </active>
           <depth> _ => CD </depth>
           <singleCall> _ => SINGLEPRANK </singleCall>
         </prank>
```

- `#endPrank` will end the prank, restoring the previous caller and origin to the `<caller>` and `<origin>` cells in the configuration.
If the production is matched when no prank is active, it will be ignored.

```k
    syntax KItem ::= "#endPrank" [klabel(foundry_endPrank)]
 // -------------------------------------------------------
    rule <k> #endPrank => #if SINGLECALL #then #clearPrank #else .K #fi ... </k>
        <id> _ => CL </id>
        <origin> _ => OG </origin>
        <prank>
          <prevCaller> CL </prevCaller>
          <prevOrigin> OG </prevOrigin>
          <active> true </active>
          <singleCall> SINGLECALL </singleCall>
          ...
        </prank>

    rule <k> #endPrank => .K ... </k>
        <prank>
          <active> false </active>
          ...
        </prank>
```

- `#clearPrank` will clear the prank subconfiguration.

```k
    syntax KItem ::= "#clearPrank" [klabel(foundry_clearPrank)]
 // -----------------------------------------------------------
    rule <k> #clearPrank => .K ... </k>
        <prank>
          <prevCaller> _ => .Account </prevCaller>
          <prevOrigin> _ => .Account </prevOrigin>
          <newCaller> _ => .Account </newCaller>
          <newOrigin> _ => .Account </newOrigin>
          <active> _ => false </active>
          <depth> _ => 0 </depth>
          <singleCall> _ => false </singleCall>
        </prank>
```

- `#injectPrank` replaces the current account and the origin with the pranked values.

```k
    syntax KItem ::= "#injectPrank" [klabel(foundry_inject)]
 // --------------------------------------------------------
    rule <k> #injectPrank => .K ... </k>
         <id> _ => NCL </id>
         <prank>
            <newCaller> NCL:Int </newCaller>
            <newOrigin> .Account </newOrigin>
            <active> true </active>
            ...
         </prank>

    rule <k> #injectPrank => .K ... </k>
         <id> _ => NCL </id>
         <origin> _ => NOG </origin>
         <prank>
            <newCaller> NCL:Int </newCaller>
            <newOrigin> NOG:Int </newOrigin>
            <active> true </active>
            ...
         </prank>
```

```k
    syntax Bytes ::= #sign ( Bytes , Bytes ) [function,klabel(foundry_sign)]
 // ------------------------------------------------------------------------
    rule #sign(BA1, BA2) => #parseByteStack(ECDSASign(BA1, BA2)) [concrete]
```

- `#setExpectEmit` will initialize the `<expectEmit/>` subconfiguration, based on the arguments provided with the `expectEmit` cheat code.

```k
    syntax KItem ::= "#setExpectEmit" Bool Bool Bool Bool Account [klabel(foundry_setExpectEmit)]
 // ---------------------------------------------------------------------------------------------
    rule <k> #setExpectEmit T1 T2 T3 CHECKDATA ACCT => .K ... </k>
         <expectEmit>
           <recordEvent> _ => true </recordEvent>
           <isEventExpected> _ => false </isEventExpected>
           <checkedTopics> _ => ListItem(true) ListItem(T1) ListItem(T2) ListItem(T3) .List </checkedTopics>
           <checkedData> _ => CHECKDATA </checkedData>
           <expectedEventAddress> _ => ACCT </expectedEventAddress>
         </expectEmit>
```

- `#clearExpectEmit` is used to clear the `<expectEmit/>` subconfiguration and restore initial values.

```k
    syntax KItem ::= "#clearExpectEmit" [klabel(foundry_clearExpectEmit)]
 // ---------------------------------------------------------------------
    rule <k> #clearExpectEmit => .K ... </k>
         <expectEmit>
           <recordEvent> _ => false </recordEvent>
           <isEventExpected> _ => false </isEventExpected>
           <checkedTopics> _ => .List </checkedTopics>
           <checkedData> _ => false </checkedData>
           <expectedEventAddress> _ => .Account </expectedEventAddress>
         </expectEmit>
```

- `#checkTopics` handles the comparison of two topic lists, guided by a list of boolean flags indicating which topics to compare.
It validates that the lists are of equal length before comparing topics as dictated by the boolean flags.

- `#checkTopic` decides if two topics should be compared based on a boolean flag.
If the flag is false, it skips comparison, assuming success; otherwise, it compares the topics for equality.

```k
    syntax Bool ::= "#checkTopic" "(" Bool "," Int "," Int ")" [function, klabel(foundry_checkTopic)]
                  | "#checkTopics" "(" List "," List "," List ")" [function, klabel(foundry_checkTopics)]
 // -----------------------------------------------------------------------------------------------------
    rule #checkTopic(CHECK, V1, V2) => (notBool CHECK) orBool (V1 ==Int V2)

    rule #checkTopics(.List, _, _) => true
    rule #checkTopics(_ , .List, .List) => true
    rule #checkTopics(_, L1, L2) => false requires notBool size(L1) ==Int size(L2)
    rule #checkTopics(ListItem(CHECK) CHECKS, ListItem(V1) L1, ListItem(V2) L2) => #checkTopic(CHECK, V1, V2) andBool #checkTopics(CHECKS, L1, L2) requires size(L1) ==Int size(L2)
```

- `#addAddressToWhitelist` enables the whitelist restriction for calls and adds an address to the whitelist.

```k
    syntax KItem ::= "#addAddressToWhitelist" Int [klabel(foundry_addAddressToWhitelist)]
 // -------------------------------------------------------------------------------------
    rule <k> #addAddressToWhitelist ACCT => .K ... </k>
        <whitelist>
          <isCallWhitelistActive> _ => true </isCallWhitelistActive>
          <addressSet>  WLIST => WLIST SetItem(ACCT) </addressSet>
          ...
        </whitelist>
```

- `#addStorageSlotToWhitelist` enables the whitelist restriction for storage chagnes and adds a `StorageSlot` item to the whitelist.

```k
    syntax KItem ::= "#addStorageSlotToWhitelist" StorageSlot [klabel(foundry_addStorageSlotToWhitelist)]
 // -----------------------------------------------------------------------------------------------------
    rule <k> #addStorageSlotToWhitelist SLOT => .K ... </k>
        <whitelist>
          <isStorageWhitelistActive> _ => true </isStorageWhitelistActive>
          <storageSlotSet> WLIST => WLIST SetItem(SLOT) </storageSlotSet>
          ...
        </whitelist>
```

- `#etchAccountIfEmpty Account` - sets an Account code to a single byte '0u8' if the account is empty to circumvent the `extcodesize` check that Solidity might perform ([source](https://github.com/foundry-rs/foundry/blob/b78289a0bc9df6e35624c632396e16f27d4ccb3f/crates/cheatcodes/src/evm/mock.rs#L54)).

```k
    syntax KItem ::= "#etchAccountIfEmpty" Account [klabel(foundry_etchAccountIfEmpty)]
 // -----------------------------------------------------------------------------------
    rule <k> #etchAccountIfEmpty ACCT => .K ... </k>
         <accounts>
           <account>
             <acctID> ACCT </acctID>
             <code> CODE => #bufStrict(1,0) </code>
             ...
           </account>
           ...
         </accounts>
      requires lengthBytes(CODE) ==Int 0
    rule <k> #etchAccountIfEmpty _ => .K ... </k> [owise]
```

- `#setMockCall MOCKADDRESS MOCKCALLDATA MOCKRETURN` will update the `<mockcalls>` mapping for the given account.

```k
    syntax KItem ::= "#setMockCall" Account Bytes Bytes [klabel(foundry_setMockCall)]
 // ---------------------------------------------------------------------------------
    rule <k> #setMockCall MOCKADDRESS MOCKCALLDATA MOCKRETURN => .K ... </k>
         <mockCall>
            <mockAddress> MOCKADDRESS </mockAddress>
            <mockValues>  MOCKVALUES => MOCKVALUES [ MOCKCALLDATA <- MOCKRETURN ] </mockValues>
         </mockCall>

   rule <k> #setMockCall MOCKADDRESS MOCKCALLDATA MOCKRETURN => .K ... </k>
         <mockCalls>
           ( .Bag
            => <mockCall>
                  <mockAddress> MOCKADDRESS </mockAddress>
                  <mockValues> .Map [ MOCKCALLDATA <- MOCKRETURN ] </mockValues>
               </mockCall>
           )
           ...
         </mockCalls>
```

- `#execMockCall` will update the output of the function call with `RETURNDATA` using `#setLocalMem`. In case the function did not end with `EVMC_SUCCESS` it will update the status code to `EVMC_SUCCESS`. 

```k
    syntax KItem ::= "#execMockCall" Int Int Bytes [klabel(foundry_execMockCall)]
 // -----------------------------------------------------------------------------
    rule <k> #execMockCall RETSTART RETWIDTH RETURNDATA => 1 ~> #push ~> #setLocalMem RETSTART RETWIDTH RETURNDATA ... </k>
         <output> _ => RETURNDATA </output>
         <wordStack> _ : WS => 1 : WS </wordStack>
```

- selectors for cheat code functions.

```k
    rule ( selector ( "assume(bool)" )                             => 1281615202 )
    rule ( selector ( "deal(address,uint256)" )                    => 3364511341 )
    rule ( selector ( "etch(address,bytes)" )                      => 3033974658 )
    rule ( selector ( "warp(uint256)" )                            => 3856056066 )
    rule ( selector ( "roll(uint256)" )                            => 528174896  )
    rule ( selector ( "fee(uint256)" )                             => 968063664  )
    rule ( selector ( "chainId(uint256)" )                         => 1078582738 )
    rule ( selector ( "coinbase(address)" )                        => 4282924116 )
    rule ( selector ( "label(address,string)" )                    => 3327641368 )
    rule ( selector ( "getNonce(address)" )                        => 755185067  )
    rule ( selector ( "addr(uint256)" )                            => 4288775753 )
    rule ( selector ( "load(address,bytes32)" )                    => 1719639408 )
    rule ( selector ( "store(address,bytes32,bytes32)" )           => 1892290747 )
    rule ( selector ( "setNonce(address,uint64)" )                 => 4175530839 )
    rule ( selector ( "expectRevert()" )                           => 4102309908 )
    rule ( selector ( "expectRevert(bytes)" )                      => 4069379763 )
    rule ( selector ( "startPrank(address)" )                      => 105151830  )
    rule ( selector ( "startPrank(address,address)" )              => 1169514616 )
    rule ( selector ( "stopPrank()" )                              => 2428830011 )
    rule ( selector ( "expectStaticCall(address,bytes)" )          => 2232945516 )
    rule ( selector ( "expectDelegateCall(address,bytes)" )        => 1030406631 )
    rule ( selector ( "expectRegularCall(address,uint256,bytes)" ) => 1973496647 )
    rule ( selector ( "expectCreate(address,uint256,bytes)" )      => 658968394  )
    rule ( selector ( "expectCreate2(address,uint256,bytes)" )     => 3854582462 )
    rule ( selector ( "expectEmit(bool,bool,bool,bool)" )          => 1226622914 )
    rule ( selector ( "expectEmit(bool,bool,bool,bool,address)" )  => 2176505587 )
    rule ( selector ( "sign(uint256,bytes32)" )                    => 3812747940 )
    rule ( selector ( "symbolicStorage(address)" )                 => 769677742  )
    rule ( selector ( "freshUInt(uint8)" )                         => 625253732  )
    rule ( selector ( "freshBool()" )                              => 2935720297 )
    rule ( selector ( "freshBytes(uint256)" )                      => 1389402351 )
    rule ( selector ( "prank(address)" )                           => 3395723175 )
    rule ( selector ( "prank(address,address)" )                   => 1206193358 )
    rule ( selector ( "allowCallsToAddress(address)" )             => 1850795572 )
    rule ( selector ( "allowChangesToStorage(address,uint256)" )   => 4207417100 )
    rule ( selector ( "infiniteGas()" )                            => 3986649939 )
    rule ( selector ( "setGas(uint256)" )                          => 3713137314 )
    rule ( selector ( "mockCall(address,bytes,bytes)" )            => 3110212580 )
```

- selectors for unimplemented cheat code functions.

```k
    rule selector ( "expectRegularCall(address,bytes)" )        => 3178868520
    rule selector ( "expectNoCall()" )                          => 3861374088
    rule selector ( "ffi(string[])" )                           => 2299921511
    rule selector ( "setEnv(string,string)" )                   => 1029252078
    rule selector ( "envBool(string)" )                         => 2127686781
    rule selector ( "envUint(string)" )                         => 3247934751
    rule selector ( "envInt(string)" )                          => 2301234273
    rule selector ( "envAddress(string)" )                      => 890066623
    rule selector ( "envBytes32(string)" )                      => 2543095874
    rule selector ( "envString(string)" )                       => 4168600345
    rule selector ( "envBytes(string)" )                        => 1299951366
    rule selector ( "envBool(string,string)" )                  => 2863521455
    rule selector ( "envUint(string,string)" )                  => 4091461785
    rule selector ( "envInt(string,string)" )                   => 1108873552
    rule selector ( "envAddress(string,string)" )               => 2905717242
    rule selector ( "envBytes32(string,string)" )               => 1525821889
    rule selector ( "envString(string,string)" )                => 347089865
    rule selector ( "envBytes(string,string)" )                 => 3720504603
    rule selector ( "expectRevert(bytes4)" )                    => 3273568480
    rule selector ( "record()" )                                => 644673801
    rule selector ( "accesses(address)" )                       => 1706857601
    rule selector ( "mockCall(address,uint256,bytes,bytes)" )   => 2168494993
    rule selector ( "clearMockedCalls()" )                      => 1071599125
    rule selector ( "expectCall(address,bytes)" )               => 3177903156
    rule selector ( "expectCall(address,uint256,bytes)" )       => 4077681571
    rule selector ( "getCode(string)" )                         => 2367473957
    rule selector ( "broadcast()" )                             => 2949218368
    rule selector ( "broadcast(address)" )                      => 3868601563
    rule selector ( "startBroadcast()" )                        => 2142579071
    rule selector ( "startBroadcast(address)" )                 => 2146183821
    rule selector ( "stopBroadcast()" )                         => 1995103542
    rule selector ( "readFile(string)" )                        => 1626979089
    rule selector ( "readLine(string)" )                        => 1895126824
    rule selector ( "writeFile(string,string)" )                => 2306738839
    rule selector ( "writeLine(string,string)" )                => 1637714303
    rule selector ( "closeFile(string)" )                       => 1220748319
    rule selector ( "removeFile(string)" )                      => 4054835277
    rule selector ( "toString(address)" )                       => 1456103998
    rule selector ( "toString(bytes)" )                         => 1907020045
    rule selector ( "toString(bytes32)" )                       => 2971277800
    rule selector ( "toString(bool)" )                          => 1910302682
    rule selector ( "toString(uint256)" )                       => 1761649582
    rule selector ( "toString(int256)" )                        => 2736964622
    rule selector ( "recordLogs()" )                            => 1101999954
    rule selector ( "getRecordedLogs()" )                       => 420828068
    rule selector ( "snapshot()" )                              => 2534502746
    rule selector ( "revertTo(uint256)" )                       => 1155002532
    rule selector ( "createFork(string,uint256)" )              => 1805892139
    rule selector ( "createFork(string)" )                      => 834286744
    rule selector ( "createSelectFork(string,uint256)" )        => 1911440973
    rule selector ( "createSelectFork(string)" )                => 2556952628
    rule selector ( "selectFork(uint256)" )                     => 2663344167
    rule selector ( "activeFork()" )                            => 789593890
    rule selector ( "rollFork(uint256)" )                       => 3652973473
    rule selector ( "rollFork(uint256,uint256)" )               => 3612115876
    rule selector ( "rpcUrl(string)" )                          => 2539285737
    rule selector ( "rpcUrls()" )                               => 2824504344
    rule selector ( "deriveKey(string,uint32)" )                => 1646872971
```

- selector for Solidity built-in Error

```k
    rule ( selector ( "Error(string)" ) => 147028384 )
```
```k
endmodule
```
