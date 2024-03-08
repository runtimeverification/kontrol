// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "src/Prank.sol";

contract PrankTest is Test {
    Prank prankContract;

    function setUp() public {
        prankContract = new Prank();
    }

    function testAddAsOwner(uint256 x) public {
        assertEq(prankContract.count(), 0);
        prankContract.add(x);
        assertEq(prankContract.count(), x);
    }

    function testFailAddPrank(uint256 x) public {
        vm.prank(address(0));
        prankContract.add(x);
    }

    function testAddStartPrank(uint256 x) public {
        vm.expectRevert(bytes("Only owner"));
        vm.startPrank(address(0));
        prankContract.add(x);
        assertEq(prankContract.count(), 0);
        vm.stopPrank();
    }


    function testSubtractFail(uint256 x) public {
        vm.expectRevert();
        prankContract.subtract(x);
        assertEq(prankContract.count(), 0);
    }

    function testSubtractAsTxOrigin(uint256 addValue, uint256 subValue) public {
        prankContract.add(addValue);
        vm.assume(subValue<=addValue);
        vm.prank(address(0), address(0));
        prankContract.subtract(subValue);
        assertEq(prankContract.count(), addValue-subValue);
    }

    function testSubtractStartPrank(uint256 addValue, uint256 subValue) public {
        prankContract.add(addValue);
        vm.startPrank(address(0),address(0));
        vm.assume(subValue<=addValue);
        prankContract.subtract(subValue);
        assertEq(prankContract.count(), addValue-subValue);
        vm.stopPrank();
    }

    function testSymbolicStartPrank(address addr) public {
        vm.startPrank(addr);
        assert(prankContract.msgSender() == addr);
        vm.stopPrank();
    }
}

contract PrankTestMsgSender is Test {
    Prank public prankcontract;

    function setUp() public {
        prankcontract = new Prank();
        vm.prank(address(0));
    }

    function test_msgsender_setup() external {
        assert(prankcontract.msgSender() == address(0)); 
    }
}

contract PrankTestOrigin is Test {
    Prank public prankcontract;

    function setUp() public {
        prankcontract = new Prank();
        vm.prank(address(0), address(0));
    }

    function test_origin_setup() external {
        assert(prankcontract.txOrigin() == address(0));
    }
}

contract StartPrankTestMsgSender is Test {
    Prank public prankcontract;

    function setUp() public {
        prankcontract = new Prank();
        vm.startPrank(address(0));
    }

    function test_startprank_msgsender_setup() external {
        assert(prankcontract.msgSender() == address(0)); 
    }
}

contract StartPrankTestOrigin is Test {
    Prank public prankcontract;

    function setUp() public {
        prankcontract = new Prank();
        vm.startPrank(address(0), address(0));
    }

    function test_startprank_origin_setup() external {
        assert(prankcontract.txOrigin() == address(0));
    }
}
