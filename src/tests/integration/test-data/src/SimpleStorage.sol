// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract SimpleStorage {
    uint256 public totalSupply;        // slot 0
    address public owner;              // slot 1
    uint256[] public balances;         // slot 2
    
    struct User {
        uint256 id;                    // slot 3, offset 0
        address wallet;                // slot 4, offset 0
        bool isActive;                 // slot 4, offset 20
    }
    
    User public currentUser;           // slots 3-4
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1000000;
        currentUser = User({
            id: 1,
            wallet: msg.sender,
            isActive: true
        });
    }
    
    function updateBalance(uint256 _amount) external {
        balances.push(_amount);
    }
    
    function updateCurrentUser(uint256 _id, address _wallet, bool _isActive) external {
        currentUser = User({
            id: _id,
            wallet: _wallet,
            isActive: _isActive
        });
    }
}
