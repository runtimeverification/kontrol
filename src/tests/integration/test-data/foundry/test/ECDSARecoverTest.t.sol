pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract ECDSARecoverTest is Test {
    function testECDSARecover(uint256 wad) public {
        payable(msg.sender).transfer(wad);
    }
}