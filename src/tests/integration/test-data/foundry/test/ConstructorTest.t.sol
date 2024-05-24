// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

// test with summary_config mode
// add test that uses separate contract with constructor

import "forge-std/Test.sol";

contract ImportedContract {
    uint256 public count;

    constructor() payable {
        count = 5;
    }

    // Compare ImportedContract.set KCFG and  ConstrucorTest.test_contract_call KCFG with and without
    // skipping constructors for summarized function contracts

    function set(uint256 x) public {
        if(count < 3){
            return;
        }
        count = x;
    }

    function add(uint256 x) public {
        count = count + x;
    }

}

contract ConstructorTest is Test {
    bool flag = true;
    ImportedContract member_contract;

    constructor() payable {
        member_contract = new ImportedContract();
        member_contract.set(4321);
    }

    function test_constructor() public {
        assert(flag);
    }

    function testFail_constructor() public {
        assert(!flag);
    }

    function run_constructor() public {
        assert(flag);
    }

    function test_contract_call() public {
        assert(flag);
        ImportedContract local_contract = new ImportedContract();
        local_contract.set(5432);

        member_contract.add(3);
        assertEq(member_contract.count(), 4324);

        local_contract.add(5);
        assertEq(local_contract.count(), 5437);
    }
    
}


