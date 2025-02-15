// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.13;

import {Test, console} from "forge-std/Test.sol";

// Simple ERC20 interface
interface IWETH {
    function balanceOf(address account) external view returns (uint256);
    function deposit() external payable;
}

contract ProviderUnitTest is Test {
    IWETH public weth;

    function setUp() public {
        // WETH address on OP Mainnet
        weth = IWETH(0x121ab82b49B2BC4c7901CA46B8277962b4350204);
    }

    function testDeposit() public {

        uint balBefore = weth.balanceOf(address(this));
        assert(balBefore == 0);

        uint amount = vm.randomUint();
        vm.deal(address(this), amount);
        weth.deposit{value: amount}();

        uint balAfter = weth.balanceOf(address(this));
        assert(balAfter == amount);
    }

    function testBalance() public view{
        uint result;
        address target = address(weth);
        assembly {
            result := balance(target)
        }
        assertGe (result , 0);
    }

    function testExtCodeSize() public view{
        uint size;
        address target = address(weth);
        assembly {
            size := extcodesize(target)
        }
        assertEq (size , 3305);
    }

    function testExtCodeCopy() public view {
        address target = address(weth);
        bytes memory code = new bytes(3305);
        assembly {
            // Copy the code starting from offset 0 into memory starting at code + 32 bytes.
            extcodecopy(target, add(code, 0x20), 0, 3305)
        }
        assert(code.length == 3305);
    }

    function testExtCodeHash() public view {
        address target = address(weth);
        bytes32 codehash;
        assembly {
            codehash := extcodehash(target)
        }

        assertEq(codehash, 0xe30dc87ed2bc929b6ab16f1548d804911bada1b629fc3982dda57627ce934acc);
    }
}

