// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract EtchTest {
    function testEtch() public pure returns (bool) {
        return true;
    }
}

contract AccountParamsTest is Test, KontrolCheats {
    function testDealConcrete() public {
        vm.deal(address(505), 256);
        assertEq(address(505).balance, 256);
    }

    function testDealSymbolic(uint256 value) public {
        vm.deal(address(328), value);
        assertEq(address(328).balance, value);
    }

    function testEtchConcreteCode() public {
        bytes memory code = bytes("this should be EVM bytecode");
        vm.etch(address(124), code);
        assertEq(address(124).code, code);
    }

    function testEtchSymbolicCode(bytes calldata code) public {
        vm.etch(address(124), code);
        assertEq(address(124).code, code);
    }

    function testEtchSymbolicAddress() public {
        address etchAddr = kevm.freshAddress();
        // `etchAddr` is not 0 or precompiled address
        vm.assume(etchAddr > address(9));
      
        bytes memory etchCode = bytes(hex"6080604052348015600f57600080fd5b506004361060285760003560e01c80631a9f8ff714602d575b600080fd5b604080516001815290519081900360200190f3fea2646970667358221220c2310c11ffdfaaecbc61aff49cac6de28e626e3aef1fcf4857565c0e6a87715c64736f6c634300080d0033");

        vm.etch(etchAddr, etchCode);
      
        bool result = EtchTest(etchAddr).testEtch();
        assertTrue(result);
    }

    function testNonceSymbolic(uint64 newNonce) public {
       uint64 oldNonce = vm.getNonce(address(this));
       vm.assume(newNonce > oldNonce);
       vm.setNonce(address(this), newNonce);
       assert(vm.getNonce(address(this)) == newNonce);
    }

    function test_GetNonce_true() public {
       uint64 nonce = vm.getNonce(address(this));
       assert(nonce == 1);
    }

    function test_getNonce_unknownSymbolic(address addr) public {
      vm.assume(addr != address(vm));
      vm.assume(addr != address(this));
      vm.assume(addr != address(0x3fAB184622Dc19b6109349B94811493BF2a45362));
      vm.assume(addr != address(0x4e59b44847b379578588920cA78FbF26c0B4956C));
      uint64 nonce = vm.getNonce(addr);
      assert(nonce == 0);
    }

    function test_GetNonce_false() public {
       uint64 nonce = vm.getNonce(address(100));
       assertEq(nonce, 10);
    }

    function testFail_GetNonce_true() public {
       uint64 nonce = vm.getNonce(address(0));
       assertEq(nonce, 10);
    }

    function testFail_GetNonce_false() public {
       uint64 nonce = vm.getNonce(address(this));
       assertEq(nonce, 1);
    }

    function test_Nonce_ExistentAddress() public {
       vm.setNonce(address(this), 100);
       uint64 nonce = vm.getNonce(address(this));
       assert(nonce == 100);
    }

    function test_Nonce_NonExistentAddress() public {
       vm.setNonce(address(100), 100);
       uint64 nonce = vm.getNonce(address(100));
       assert(nonce == 100);
    }
}
