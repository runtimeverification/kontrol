// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

contract SimpleStorage {
    uint256 public totalSupply;
    address public owner;
    uint256[] public balances;
    
    struct User {
        uint256 id;
        address wallet;
        bool isActive;
        uint256 lastSeen;
    }
    
    mapping(address => User) public users;
    mapping(address => uint256) public allowances;
    
    constructor() {
        owner = msg.sender;
        totalSupply = 1000000;
    }
    
    function addUser(address _wallet, uint256 _id) external {
        users[_wallet] = User({
            id: _id,
            wallet: _wallet,
            isActive: true,
            lastSeen: block.timestamp
        });
    }
    
    function updateBalance(uint256 _amount) external {
        balances.push(_amount);
    }
}
