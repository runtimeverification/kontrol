// SPDX-License-Identifier: MIT
pragma solidity >=0.6.2 <0.9.0;
pragma experimental ABIEncoderV2;

interface KEVMCheatsBase {
    // Expects a call using the CALL opcode to an address with the specified calldata.
    function expectRegularCall(address,bytes calldata) external;
    // Expects a call using the CALL opcode to an address with the specified msg.value and calldata.
    function expectRegularCall(address,uint256,bytes calldata) external;
    // Expects a static call to an address with the specified calldata.
    function expectStaticCall(address,bytes calldata) external;
    // Expects a delegate call to an address with the specified calldata.
    function expectDelegateCall(address,bytes calldata) external;
    // Expects that no contract calls are made after invoking the cheatcode.
    function expectNoCall() external;
    // Expects the given address to deploy a new contract, using the CREATE opcode, with the specified value and bytecode.
    function expectCreate(address,uint256,bytes calldata) external;
    // Expects the given address to deploy a new contract, using the CREATE2 opcode, with the specified value and bytecode (appended with a bytes32 salt).
    function expectCreate2(address,uint256,bytes calldata) external;
    // Makes the storage of the given address completely symbolic.
    function symbolicStorage(address) external;
    // Adds an address to the whitelist.
    function allowCallsToAddress(address) external;
    // Adds an address and a storage slot to the whitelist.
    function allowChangesToStorage(address,uint256) external;
    // Sets the remaining gas to an infinite value.
    function infiniteGas() external;
    // Sets the current <gas> cell to the supplied amount.
    function setGas(uint256) external;
    // Returns a symbolic unsigned integer
    function freshUInt(uint8) external returns (uint256);
    // Returns a symbolic boolean value
    function freshBool() external returns (uint256);
    // Returns a symbolic byte array
    function freshBytes(uint256) external returns (bytes memory);
}

abstract contract KEVMCheats {
    KEVMCheatsBase public constant kevm = KEVMCheatsBase(address(uint160(uint256(keccak256("hevm cheat code")))));

    // Checks if an address matches one of the built-in addresses.
    function notBuiltinAddress(address addr) internal pure returns (bool) {
        return (addr != address(645326474426547203313410069153905908525362434349) &&
                addr != address(728815563385977040452943777879061427756277306518));
    }
}
