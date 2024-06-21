// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract MappingContract {
    mapping(address => mapping(address => uint256)) public balances;
    mapping(address => uint256) public single_map;

    function get_mapping_val(address a) public returns (uint256) {
        return balances[a][a];
    }

    function get_mapping_val2(address a) public returns (uint256) {
        return single_map[a];
    }
}

contract MappingTest is Test {
  uint256 val;
  uint256 val2;
  MappingContract c;

  constructor() public {
      c = new MappingContract();
  }

  function test_mapping(address a) public {
      val = c.get_mapping_val(a);
      val2 = c.get_mapping_val2(a);
      assert(val < 256);
      assert(val2 < 256);
  }

}
