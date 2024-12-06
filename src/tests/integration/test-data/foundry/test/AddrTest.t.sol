// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract AddrTest is Test, KontrolCheats {

    function test_addr(uint256 pk) public pure {
        address alice = vm.addr(1);
        assertEq(alice, 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf);
        vm.assume(pk != 0);
        vm.assume(pk < 115792089237316195423570985008687907852837564279074904382605163141518161494337);
        address bob = vm.addr(pk);
    }

    function test_notBuiltinAddress(address addr) public pure {
        vm.assume(addr != address(728815563385977040452943777879061427756277306518));
        vm.assume(addr != address(645326474426547203313410069153905908525362434349));
        assertTrue(notBuiltinAddress(addr));
        assertTrue(notBuiltinAddress(address(110)));

    }

    function test_builtInAddresses() public view {
        assertEq(address(this), address(728815563385977040452943777879061427756277306518));
        assertEq(address(vm), address(645326474426547203313410069153905908525362434349));
    }
}
