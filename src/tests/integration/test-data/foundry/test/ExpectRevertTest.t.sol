// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract Reverter {
    error NotAuthorised(address caller, string message);

    function revertWithoutReason() public pure {
        revert();
    }

    function revertWithReason(string calldata _a) public pure {
        revert(_a);
    }

    function revertWithError(address controller, string calldata message) public pure {
        revert NotAuthorised(controller, message);
    }

    function noRevert() public pure returns (bool) {
        return true;
    }

    function returnBytesUnless(bool revertInstead)
        public pure
        returns (bytes memory)
    {
        if (revertInstead) {
            revert("Error");
        } else {
            return abi.encodePacked(bytes4(0xdeadbeef));
        }
    }

    function returnTupleUnless(bool revertInstead)
        public pure
        returns (uint256, uint256)
    {
        if (revertInstead) {
            revert("Error");
        } else {
            return (1, 2);
        }
    }
}

contract DepthReverter {
    Reverter reverter;

    constructor() {
        reverter = new Reverter();
    }

    function revertAtNextDepth() public view {
        reverter.revertWithoutReason();
    }
}

contract ExpectRevertTest is Test {
    error NotAuthorised(address caller, string message);
    Reverter reverter ;
    DepthReverter depth_reverter;

    function doRevert() internal pure {
        require(false, "");
    }

    function revertDepth2() public pure {
        revert ("This should be at depth 2");
    }
    function revertDepth1() public view {
        try this.revertDepth2()
        {} catch {}
        revert ("This should be at depth 1");
    }

    function setUp() public {
        reverter = new Reverter();
        depth_reverter = new DepthReverter();
    }

    function test_expectRevert_inDepth() public {
        vm.expectRevert("This should be at depth 1");
        this.revertDepth1();
    }

    function test_expectRevert_internalCall() public {
        vm.expectRevert();
        doRevert();
    }

    function test_expectRevert_true() public {
        vm.expectRevert();
        reverter.revertWithoutReason();
    }

    function testFail_expectRevert_false() public {
        vm.expectRevert();
        reverter.noRevert();
    }

    function test_expectRevert_message() public {
        vm.expectRevert(bytes("Revert Reason Here"));
        reverter.revertWithReason("Revert Reason Here");
    }

    function testFail_expectRevert_bytes4() public {
        vm.expectRevert(bytes4("FAIL"));
        reverter.revertWithReason("But fail.");
    }

    function test_expectRevert_bytes4() public {
        vm.expectRevert(bytes4("FAIL"));
        reverter.revertWithReason("FAIL");
    }

    function testFail_expectRevert_empty() public {
        vm.expectRevert();
    }

    function testFail_expectRevert_multipleReverts() public {
        vm.expectRevert();
        reverter.revertWithoutReason();
        reverter.revertWithoutReason();
    }

    function test_ExpectRevert_increasedDepth() public {
        vm.expectRevert();
        depth_reverter.revertAtNextDepth();
    }

    function testFail_ExpectRevert_failAndSuccess() public {
         vm.expectRevert();
         reverter.noRevert();
         vm.expectRevert();
         reverter.revertWithoutReason();
    }

    function test_expectRevert_encodedSymbolic(address controller) public {
        vm.startPrank(controller);
        vm.expectRevert(
            abi.encodeWithSelector(
                NotAuthorised.selector,
                controller,
                "TRANSFEROWNERSHIP"
            )
        );
        reverter.revertWithError(controller, "TRANSFEROWNERSHIP");
    }

    function test_expectRevert_returnValue() public {
        vm.expectRevert("Error");
        bytes memory returnValueBytes = reverter.returnBytesUnless(true);
        assertEq0(returnValueBytes, "");

        vm.expectRevert("Error");
        (uint256 fst, uint256 snd) = reverter.returnTupleUnless(true);
        assertEq(fst, 0);
        assertEq(snd, 0);
    }
}
