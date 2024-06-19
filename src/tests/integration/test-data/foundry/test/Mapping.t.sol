// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract MappingContract {
    mapping(address => mapping(address => uint256)) public balances;

    function get_mapping_val(address a) public returns (uint256) {
        return balances[a][a];
    }
}

contract MappingTest is Test {
  uint256 b;
  uint256 val;
  MappingContract c;

  constructor() public {
      c = new MappingContract();
  }

  function test_mapping(address a) public {
      b = 42;
      val = c.get_mapping_val(a);
      assert(val < 256);
  }

}
