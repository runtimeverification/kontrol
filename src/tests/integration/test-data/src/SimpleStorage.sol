// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract SimpleStorage {
    uint256 public totalSupply;        // slot 0
    address public owner;              // slot 1
    uint256[] public balances;         // slot 2
    
    // Packed variables in slot 3
    uint128 public packedUint1;        // slot 3, offset 0
    uint64 public packedUint2;         // slot 3, offset 16
    uint32 public packedUint3;         // slot 3, offset 24
    uint16 public packedUint4;         // slot 3, offset 28
    uint8 public packedUint5;          // slot 3, offset 30
    bool public packedBool;            // slot 3, offset 31
    
    // Struct stored directly in storage
    struct User {
        uint256 id;                    // slot 4, offset 0
        address wallet;                // slot 5, offset 0
        bool isActive;                 // slot 6, offset 0
        uint64 lastSeen;               // slot 6, offset 1
    }
    
    User public currentUser;           // slots 4-6
    
    mapping(address => User) public users;     // slot 7
    mapping(address => uint256) public allowances; // slot 8
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1000000;
        packedUint1 = 12345;
        packedUint2 = 67890;
        packedUint3 = 11111;
        packedUint4 = 22222;
        packedUint5 = 33;
        packedBool = true;
        
        currentUser = User({
            id: 1,
            wallet: msg.sender,
            isActive: true,
            lastSeen: uint64(block.timestamp)
        });
    }
    
    function addUser(address _wallet, uint256 _id) external {
        users[_wallet] = User({
            id: _id,
            wallet: _wallet,
            isActive: true,
            lastSeen: uint64(block.timestamp)
        });
    }
    
    function updateBalance(uint256 _amount) external {
        balances.push(_amount);
    }
    
    function updatePacked(uint128 _val1, uint64 _val2, uint32 _val3, uint16 _val4, uint8 _val5, bool _bool) external {
        packedUint1 = _val1;
        packedUint2 = _val2;
        packedUint3 = _val3;
        packedUint4 = _val4;
        packedUint5 = _val5;
        packedBool = _bool;
    }
    
    function updateCurrentUser(uint256 _id, address _wallet, bool _isActive, uint64 _lastSeen) external {
        currentUser = User({
            id: _id,
            wallet: _wallet,
            isActive: _isActive,
            lastSeen: _lastSeen
        });
    }
}
