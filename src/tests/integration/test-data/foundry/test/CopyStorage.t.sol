pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "kontrol-cheatcodes/KontrolCheats.sol";

contract CopyStorageContract {
    uint256 public x;
}

contract CopyStorageTest is Test, KontrolCheats {
    CopyStorageContract csc_1;
    CopyStorageContract csc_2;

    function _storeUInt256(address contractAddress, uint256 slot, uint256 value) internal {
        vm.store(contractAddress, bytes32(slot), bytes32(value));
    }

    function setUp() public {
        csc_1 = new CopyStorageContract();
        csc_2 = new CopyStorageContract();
    }

    function testCopyStorage() public {
        // Make the storage of first contract symbolic
        kevm.symbolicStorage(address(csc_1));
        // and explicitly put a constrained symbolic value into the slot for `x`
        uint256 x_1 = uint256(kevm.freshUInt(32));
        _storeUInt256(address(csc_1), 0, x_1);

        // `x` of second contract is uninitialized
        assert(csc_2.x() == 0);
        // Copy storage from first to second contract
        vm.copyStorage(address(csc_1), address(csc_2));
        // `x` of second contract is now the `x` of the first
        assert(csc_2.x() == x_1);
    }
}
