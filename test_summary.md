foundry-prove-all that are not skipped on booster

AccountParamsTest.testDealConcrete()
  - deal cheatcode with concrete value sets balance correctly
AccountParamsTest.testDealSymbolic(uint256)
  - deal cheatcode with symbolic value sets balance correctly
AccountParamsTest.testEtchConcrete()
  - etch cheatcode with concrete value sets code correctly
AccountParamsTest.testFail_GetNonce_true()
  - getNonce cheatcode, account nonce of 0 address is not 10
AccountParamsTest.test_GetNonce_true()
  - getNonce cheatcode the current account nonce is 1
AccountParamsTest.test_getNonce_unknownSymbolic(address)
  - getNonce cheatcode, the nonce of a symbolic account not in the configuration is 0
AccountParamsTest.test_Nonce_ExistentAddress()
  - getNonce and setNonce cheatcode, can set and get nonce of account in configuration
AccountParamsTest.test_Nonce_NonExistentAddress()
  - getNonce and setNonce cheatcode, can set and get nonce of new account not in configuration
AccountParamsTest.testNonceSymbolic(uint64)
  - getNonce and setNonce cheatcode, can set and get a symbolic account nonce value

AddrTest.test_addr_true()
  - addr cheatcode, computes address correctly
AddrTest.test_builtInAddresses()
  - contract account and VM contract account have the correct address
AddrTest.test_notBuiltinAddress_concrete()
  - notBuiltinAddress cheatcode, not equal to concrete address value
AddrTest.test_notBuiltinAddress_symbolic(address)
  - notBuiltinAddress cheatcode, not equal to symbolic address value

AllowChangesTest.testAllow()
  - allowCallsToAddress and allowChangesToStorage cheatcodes, allows changing contract values externally
AllowChangesTest.testFailAllowCallsToAddress()
  - allowCallsToAddress and allowChangesToStorage cheatcodes, values cannot be changed calling cheatcode on wrong address
AllowChangesTest.testFailAllowChangesToStorage()
  - allowCallsToAddress and allowChangesToStorage cheatcodes, values cannot be changed calling cheatcode on wrong storage slot

ArithmeticTest.test_max1(uint256,uint256)
  - custom max function, test with symbolic values, assume one is geq to the other
ArithmeticTest.test_max2(uint256,uint256)
  - custom max function, test with symbolic values, assert result is geq to both inputs
AssertTest.test_assert_true()
  - assert true
AssertTest.test_assert_true_branch(uint256)
  - set number relative to symbolic input on two different branches and assert relation to input
AssertTest.checkFail_assert_false()
  - assert false

AssumeTest.test_assume_staticCall(bool)
  - assume a symbolic boolean value inside a static call and then assert that same value
AssumeTest.test_assume_true(uint256,uint256)
  - assume and then assert two variables are equal
AssumeTest.testFail_assume_true(uint256,uint256)
  - assume and two variables are not equal and assert that they are
AssumeTest.test_multi_assume(address,address)
  - make multiple assumptions about inputs not being equal to various addresses

BlockParamsTest.testBlockNumber()
  - assert current block number is nonnegative
BlockParamsTest.testChainId(uint256)
  - use cheatcode to set chainID to a symbolic value
BlockParamsTest.testCoinBase()
  - use cheatcode to set coinBase to a concrete value
BlockParamsTest.testFee(uint256)
  - use cheatcode to set fee to a symbolic value
BlockParamsTest.testRoll(uint256)
  - use roll cheatcode to roll to a symbolic new block number
BlockParamsTest.testWarp(uint256)
  - use warp cheatcode to set timestamp to a symbolic value
  
BMCLoopsTest.test_countdown_concrete()
  - count down with a loop from a concrete value of 3
BMCLoopsTest.test_countdown_symbolic(uint256)
  - count down with a loop from a concrete value, assumed to be leq 3

BytesTypeTest.test_bytes4(bytes4)
  - assert symbolic bytes4 value converted to uint32 is leq maximum uint32 value
BytesTypeTest.test_bytes4_fail(bytes4)
  - assert symbolic bytes4 value converted to uint32 is greater than maximum uint32 value

CounterTest.testIncrement()
  - test creation of Counter contract and both its functions
CounterTest.testSetNumber(uint256)
  - test creation of Counter contract and set its number to a symbolic value

EmitContractTest.testExpectEmit()
  - test expectEmit cheatcode
EmitContractTest.testExpectEmitCheckEmitter()
  - test expectEmit cheatcode, additionally check emitter address is correct
EmitContractTest.testExpectEmitDoNotCheckData()
  - test expectEmit cheatcode with divergent data, but specify not to check data

ExpectCallTest.testExpectRegularCall()
  - test expectRegularCall cheatcode
ExpectCallTest.testExpectStaticCall()
  - test expectStaticCall cheatcode

ExpectRevertTest.test_ExpectRevert_increasedDepth()
  - test expectRevert cheatcode catches revert on nested function calls
ExpectRevertTest.test_expectRevert_message()
  - test expectRevert cheatcode, asserts correct revert message is retained
ExpectRevertTest.test_expectRevert_returnValue()
  - test expectRevert cheatcode, default values are returned if function reverts
ExpectRevertTest.test_expectRevert_true()
  - test expectRevert cheatcode, basic
ExpectRevertTest.testFail_expectRevert_empty()
  - test expectRevert cheatcode, fails because no revert
ExpectRevertTest.testFail_ExpectRevert_failAndSuccess()
  - test expectRevert cheatcode, fails because one no revert and one successful expected revert
ExpectRevertTest.testFail_expectRevert_false()
  - test expectRevert cheatcode, fails because one no revert
ExpectRevertTest.testFail_expectRevert_multipleReverts()
  - test expectRevert cheatcode, fails because more reverts than expected

GasTest.testSetGas()
  - test setGas cheatcode, set gas and then check it goes doesn after some operation

LabelTest.testLabel()
  - set address label using label cheatcode

LoopsTest.sum_N(uint256)
  - generic symbolic loop sum, uses circularity lemma
LoopsTest.test_sum_10()
  - call sum_N on value of 10

MethodDisambiguateTest.test_method_call()
  - test that it is possible to disambiguate method calls based on argument types

PlainPrankTest.testFail_startPrank_internalCall()
  - test startPrank cheatcode on same contract function
PlainPrankTest.test_prank_zeroAddress_true()
  - test prank cheatcode as address 0
PlainPrankTest.test_startPrank_true()
  - startPrank and stopPrank, basic
PlainPrankTest.test_startPrankWithOrigin_true()
  - startPrank and stopPrank, also set origin field for startPrank
PlainPrankTest.test_startPrank_zeroAddress_true()
  - startPrank and stopPrank cheatcodes as address 0
PlainPrankTest.test_stopPrank_notExistent()
  - stopPrank with no corresponding startPrank

Setup2Test.testFail_setup()
  - test setUp method runs and sets fields to other value
Setup2Test.test_setup()
  - test setUp method runs and sets fields to value

SetUpDeployTest.test_extcodesize()
  - test contract deployed in setup has positive extcodesize

StoreTest.testGasLoadColdVM()
StoreTest.testGasLoadWarmUp()
StoreTest.testGasStoreColdVM()
StoreTest.testGasStoreWarmUp()
StoreTest.testLoadNonExistent()
StoreTest.testStoreLoad()
StoreTest.testStoreLoadNonExistent()
SymbolicStorageTest.testEmptyInitialStorage(uint256)
SymbolicStorageTest.testFail_SymbolicStorage(uint256)
SymbolicStorageTest.testFail_SymbolicStorage1(uint256)
UintTypeTest.test_uint256(uint256)
StructTypeTest.test_vars((uint8,uint32,bytes32))

Skipped tests:

AccountParamsTest.testEtchSymbolic(bytes)
AccountParamsTest.testFail_GetNonce_false()
AccountParamsTest.test_GetNonce_false()
AddrTest.test_addr_false()
AddrTest.test_addr_symbolic(uint256)
AddrTest.testFail_addr_false()
AddrTest.testFail_addr_true()
AllowChangesTest.test()
AllowChangesTest.testAllow_fail()
ArithmeticTest.test_decreasing_div(uint256,uint256)
ArithmeticTest.test_max1_broken(uint256,uint256)
ArithmeticTest.test_wdiv_rounding(uint256,uint256)
ArithmeticTest.test_wmul_increasing(uint256,uint256)
ArithmeticTest.test_wmul_increasing_gt_one(uint256,uint256)
ArithmeticTest.test_wmul_increasing_overflow(uint256,uint256)
ArithmeticTest.test_wmul_increasing_positive(uint256,uint256)
ArithmeticTest.test_wmul_rounding(uint256,uint256)
ArithmeticTest.test_wmul_wdiv_inverse(uint256,uint256)
ArithmeticTest.test_wmul_wdiv_inverse_underflow(uint256,uint256)
ArithmeticTest.test_wmul_weakly_increasing_positive(uint256,uint256)
AssertTest.test_assert_false()
AssertTest.testFail_assert_true()
AssertTest.testFail_expect_revert()
AssertTest.test_failing_branch(uint256)
AssertTest.test_revert_branch(uint256,uint256)
AssumeTest.test_assume_false(uint256,uint256)
AssumeTest.testFail_assume_false(uint256,uint256)
BroadcastTest.testDeploy()
BytesTypeTest.test_bytes32_fail(bytes32)
BytesTypeTest.test_bytes4_fail(bytes4)
BytesTypeTest.testFail_bytes32(bytes32)
BytesTypeTest.testFail_bytes4(bytes4)
ContractBTest.testCannotSubtract43()
ContractBTest.testFailSubtract43()
ContractBTest.testNumberIs42()
ContractTest.testExample()
EnvTest.testEnvAddress()
EnvTest.testEnvAddresseArray()
EnvTest.testEnvBool()
EnvTest.testEnvBoolArray()
EnvTest.testEnvBytes()
EnvTest.testEnvBytes32()
EnvTest.testEnvBytes32Array()
EnvTest.testEnvBytesArray()
EnvTest.testEnvInt()
EnvTest.testEnvIntArray()
EnvTest.testEnvString()
EnvTest.testEnvStringArray()
EnvTest.testEnvUInt()
EnvTest.testEnvUIntArray()
ExpectRevertTest.test_expectRevert_bytes4()
ExpectRevertTest.test_expectRevert_encodedSymbolic(address)
ExpectRevertTest.test_expectRevert_internalCall()
ExpectRevertTest.testFail_expectRevert_bytes4()
FfiTest.testffi()
FfiTest.testFFIFOO()
FfiTest.testFFIScript()
FfiTest.testFFIScript2()
FilesTest.testFailRemoveFile()
FilesTest.testReadWriteFile()
FilesTest.testReadWriteLine()
ForkTest.testActiveFork()
ForkTest.testAllRPCUrl()
ForkTest.testCreateFork()
ForkTest.testCreateForkBlock()
ForkTest.testCreateSelectFork()
ForkTest.testCreateSelectForkBlock()
ForkTest.testRollFork()
ForkTest.testRollForkId()
ForkTest.testRPCUrl()
ForkTest.testRPCUrlRevert()
GasTest.testInfiniteGas()
GetCodeTest.testGetCode()
LoopsTest.testIsNotPrime(uint256)
LoopsTest.testIsPrime(uint256,uint256)
LoopsTest.testIsPrimeBroken(uint256,uint256)
LoopsTest.testIsPrimeOpt(uint256)
LoopsTest.testMax(uint256[])
LoopsTest.testMaxBroken(uint256[])
LoopsTest.testNthPrime(uint256,uint256)
LoopsTest.testSort(uint256[])
LoopsTest.testSortBroken(uint256[])
LoopsTest.testSqrt(uint256)
LoopsTest.test_sum_100()
LoopsTest.test_sum_1000()
LoopsTest.testSumToN(uint256)
LoopsTest.testSumToNBroken(uint256)
MockCallTest.testMockCall()
MockCallTest.testMockCalls()
MockCallTest.testMockCallValue()
OwnerUpOnlyTest.testFailIncrementAsNotOwner()
OwnerUpOnlyTest.testIncrementAsNotOwner()
OwnerUpOnlyTest.testIncrementAsOwner()
PlainPrankTest.testFail_startPrank_existingAlready()
PrankTest.testAddAsOwner(uint256)
PrankTest.testAddStartPrank(uint256)
PrankTest.testFailAddPrank(uint256)
PrankTest.testSubtractAsTxOrigin(uint256,uint256)
PrankTest.testSubtractFail(uint256)
PrankTest.testSubtractStartPrank(uint256,uint256)
RecordLogsTest.testRecordLogs()
SafeTest.testWithdraw()
SafeTest.testWithdrawFuzz(uint96)
SetUpTest.testSetUpCalled()
SetUpTest.testSetUpCalledSymbolic(uint256)
SignTest.testSign()
SignTest.testSign_symbolic(uint256)
SnapshotTest.testSnapshot()
StoreTest.testAccesses()
StoreTest.testGasLoadWarmVM()
StoreTest.testGasStoreWarmVM()
ToStringTest.testAddressToString()
ToStringTest.testBoolToString()
ToStringTest.testBytes32ToString()
ToStringTest.testBytesToString()
ToStringTest.testIntToString()
ToStringTest.testUint256ToString()
UintTypeTest.testFail_uint104(uint104)
UintTypeTest.testFail_uint112(uint112)
UintTypeTest.testFail_uint120(uint120)
UintTypeTest.testFail_uint128(uint128)
UintTypeTest.testFail_uint136(uint136)
UintTypeTest.testFail_uint144(uint144)
UintTypeTest.testFail_uint152(uint152)
UintTypeTest.testFail_uint16(uint16)
UintTypeTest.testFail_uint160(uint160)
UintTypeTest.testFail_uint168(uint168)
UintTypeTest.testFail_uint176(uint176)
UintTypeTest.testFail_uint184(uint184)
UintTypeTest.testFail_uint192(uint192)
UintTypeTest.testFail_uint200(uint200)
UintTypeTest.testFail_uint208(uint208)
UintTypeTest.testFail_uint216(uint216)
UintTypeTest.testFail_uint224(uint224)
UintTypeTest.testFail_uint232(uint232)
UintTypeTest.testFail_uint24(uint24)
UintTypeTest.testFail_uint240(uint240)
UintTypeTest.testFail_uint248(uint248)
UintTypeTest.testFail_uint256(uint256)
UintTypeTest.testFail_uint32(uint32)
UintTypeTest.testFail_uint40(uint40)
UintTypeTest.testFail_uint48(uint48)
UintTypeTest.testFail_uint56(uint56)
UintTypeTest.testFail_uint64(uint64)
UintTypeTest.testFail_uint72(uint72)
UintTypeTest.testFail_uint8(uint8)
UintTypeTest.testFail_uint80(uint80)
UintTypeTest.testFail_uint88(uint88)
UintTypeTest.testFail_uint96(uint96)
UintTypeTest.test_uint104(uint104)
UintTypeTest.test_uint104_fail(uint104)
UintTypeTest.test_uint112(uint112)
UintTypeTest.test_uint112_fail(uint112)
UintTypeTest.test_uint120(uint120)
UintTypeTest.test_uint120_fail(uint120)
UintTypeTest.test_uint128(uint128)
UintTypeTest.test_uint128_fail(uint128)
UintTypeTest.test_uint136(uint136)
UintTypeTest.test_uint136_fail(uint136)
UintTypeTest.test_uint144(uint144)
UintTypeTest.test_uint144_fail(uint144)
UintTypeTest.test_uint152(uint152)
UintTypeTest.test_uint152_fail(uint152)
UintTypeTest.test_uint16(uint16)
UintTypeTest.test_uint160(uint160)
UintTypeTest.test_uint160_fail(uint160)
UintTypeTest.test_uint168(uint168)
UintTypeTest.test_uint168_fail(uint168)
UintTypeTest.test_uint16_fail(uint16)
UintTypeTest.test_uint176(uint176)
UintTypeTest.test_uint176_fail(uint176)
UintTypeTest.test_uint184(uint184)
UintTypeTest.test_uint184_fail(uint184)
UintTypeTest.test_uint192(uint192)
UintTypeTest.test_uint192_fail(uint192)
UintTypeTest.test_uint200(uint200)
UintTypeTest.test_uint200_fail(uint200)
UintTypeTest.test_uint208(uint208)
UintTypeTest.test_uint208_fail(uint208)
UintTypeTest.test_uint216(uint216)
UintTypeTest.test_uint216_fail(uint216)
UintTypeTest.test_uint224(uint224)
UintTypeTest.test_uint224_fail(uint224)
UintTypeTest.test_uint232(uint232)
UintTypeTest.test_uint232_fail(uint232)
UintTypeTest.test_uint24(uint24)
UintTypeTest.test_uint240(uint240)
UintTypeTest.test_uint240_fail(uint240)
UintTypeTest.test_uint248(uint248)
UintTypeTest.test_uint248_fail(uint248)
UintTypeTest.test_uint24_fail(uint24)
UintTypeTest.test_uint256_fail(uint256)
UintTypeTest.test_uint32(uint32)
UintTypeTest.test_uint32_fail(uint32)
UintTypeTest.test_uint40(uint40)
UintTypeTest.test_uint40_fail(uint40)
UintTypeTest.test_uint48(uint48)
UintTypeTest.test_uint48_fail(uint48)
UintTypeTest.test_uint56(uint56)
UintTypeTest.test_uint56_fail(uint56)
UintTypeTest.test_uint64(uint64)
UintTypeTest.test_uint64_fail(uint64)
UintTypeTest.test_uint72(uint72)
UintTypeTest.test_uint72_fail(uint72)
UintTypeTest.test_uint8(uint8)
UintTypeTest.test_uint80(uint80)
UintTypeTest.test_uint80_fail(uint80)
UintTypeTest.test_uint88(uint88)
UintTypeTest.test_uint88_fail(uint88)
UintTypeTest.test_uint8_fail(uint8)
UintTypeTest.test_uint96(uint96)
UintTypeTest.test_uint96_fail(uint96)
IntTypeTest.testFail_int128(uint128)
IntTypeTest.testFail_int256(uint256)
IntTypeTest.testFail_int64(uint64)
IntTypeTest.test_int128(uint128)
IntTypeTest.test_int128_fail(uint128)
IntTypeTest.test_int256(uint256)
IntTypeTest.test_int256_fail(uint256)
IntTypeTest.test_int64(uint64)
IntTypeTest.test_int64_fail(uint64)


- Remove duplicate/unneccesary tests
- Check test functions do not exist which are not in the test list
- Check all tests in `test_foundry_prove.py` that they properly use booster backend
- Check updated expected output after switching file comparison tests to booster
