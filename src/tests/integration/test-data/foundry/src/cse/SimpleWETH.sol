// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import { Add, Sub } from "./Binary.sol";

// CSE challenge: initialised contract variables
// CSE challenge: global variables
// CSE challenge: contracts in storage
// CSE challenge: cross-contract function calls
// CSE challenge: mappings in storage
contract SimpleWETH {
    string public name = "Wrapped Ether";
    string public symbol = "WETH";
    uint8 public decimals = 18;

    Add add;
    Sub sub;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    fallback() external payable {
        deposit();
    }

    function deposit() public payable {
        balanceOf[msg.sender] = add.applyOp(balanceOf[msg.sender], msg.value);
    }

    function withdraw(uint256 wad) public {
        require(balanceOf[msg.sender] >= wad);
        balanceOf[msg.sender] = sub.applyOp(balanceOf[msg.sender], wad);
        payable(msg.sender).transfer(wad);
    }

    function totalSupply() public view returns (uint256) {
        return address(this).balance;
    }

    function approve(address guy, uint256 wad) public returns (bool) {
        allowance[msg.sender][guy] = wad;
        return true;
    }

    function transfer(address dst, uint256 wad) public returns (bool) {
        return transferFrom(msg.sender, dst, wad);
    }

    function transferFrom(address src, address dst, uint256 wad) public returns (bool) {
        require(balanceOf[src] >= wad);

        if (src != msg.sender && allowance[src][msg.sender] != type(uint256).max) {
            require(allowance[src][msg.sender] >= wad);
            allowance[src][msg.sender] = sub.applyOp(allowance[src][msg.sender], wad);
        }

        balanceOf[src] = sub.applyOp(balanceOf[src], wad);
        balanceOf[dst] = add.applyOp(balanceOf[dst], wad);

        return true;
    }
}