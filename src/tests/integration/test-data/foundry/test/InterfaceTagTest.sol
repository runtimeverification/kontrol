// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {Test, console} from "forge-std/Test.sol";

contract ERC20 {
    function totalSupply() public view returns (uint256) { return 15; }
}

interface IERC20 {
    /**
     * @dev Returns the value of tokens in existence.
     */
    function totalSupply() external view returns (uint256);
}

contract InterfaceContract {
    /// @custom:kontrol-instantiate-interface ERC20
    IERC20 token;

    constructor(address _token) {
        token = IERC20(_token);
    }

    function callToken() public returns (uint256) { return token.totalSupply();}
}

contract InterfaceTagTest is Test {
    InterfaceContract intContract;
    
    function setUp() public {
        ERC20 token = new ERC20();
        intContract = new InterfaceContract(address(token));
    }

    function testInterface() public {
        assert(intContract.callToken() == 15);
    }
}