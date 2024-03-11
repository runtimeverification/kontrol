// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

contract ArithmeticContract{
    function add(uint256 x, uint256 y) external pure returns (uint256 z) {
        z = x + y;
    }

    function addi(uint256 x, int128 y) external pure returns (uint256 z) {
        z = uint(int(x) + y);
    }

    function sub(uint256 x, uint256 y) external pure returns (uint256 z) {
        z = x - y;
    }

    function subi(uint256 x, int128 y) external pure returns (uint256 z) {
        z = uint(int(x) - y);
    }

    function add_sub_external(uint256 x, uint256 y, uint256 z) external view returns (uint256 res) {
        uint256 sum = this.add(x, y);
        res = sum - z;
    }
}
