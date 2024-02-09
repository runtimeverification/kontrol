// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "src/MyToken.sol";
import "src/MyIERC20.sol";
import "src/Mock.sol";


contract MockCallTest is Test {

    function testSelectorMockCall() public {
        vm.mockCall(
            address(0),
            abi.encodeWithSelector(MyToken.balanceOf.selector, address(1)),
            abi.encode(10)
        );
        assertEq(MyIERC20(address(0)).balanceOf(address(1)), 10);
    }

    function testMockCalls() public {
        vm.mockCall(
            address(0),
            abi.encodeWithSelector(MyToken.balanceOf.selector),
            abi.encode(10)
        );
        assertEq(MyIERC20(address(0)).balanceOf(address(1)), 10);
        assertEq(MyIERC20(address(0)).balanceOf(address(2)), 10);
        vm.clearMockedCalls();
    }

    function testMockCallValue() public {
        MyToken token = new MyToken(address(1337));

        assertEq(token.pay{value: 10}(address(1)), 10);
        assertEq(token.pay{value: 2}(address(2)), 2);
        vm.mockCall(
            address(token),
            10,
            abi.encodeWithSelector(MyToken.pay.selector),
            abi.encode(99)
        );
        assertEq(token.pay{value: 10}(address(1)), 99);
        assertEq(token.pay{value: 2}(address(2)), 4);
    }
}

contract MockCallTestFoundry is Test {

    function testMockGetters() public {
        Mock target = new Mock();

        // pre-mock
        assertEq(target.numberA(), 1);
        assertEq(target.numberB(), 2);

        vm.mockCall(address(target), abi.encodeWithSelector(target.numberB.selector), abi.encode(10));

        // post-mock
        assertEq(target.numberA(), 1);
        assertEq(target.numberB(), 10);
    }

    function testMockNested() public {
        Mock inner = new Mock();
        NestedMock target = new NestedMock(inner);

        // pre-mock
        assertEq(target.sum(), 3);

        vm.mockCall(address(inner), abi.encodeWithSelector(inner.numberB.selector), abi.encode(9));

        // post-mock
        assertEq(target.sum(), 10);
    }

    function testMockSelector() public {
        Mock target = new Mock();
        assertEq(target.add(5, 5), 10);

        vm.mockCall(address(target), abi.encodeWithSelector(target.add.selector), abi.encode(11));

        assertEq(target.add(5, 5), 11);
    }

    function testMockCalldata() public {
        Mock target = new Mock();
        assertEq(target.add(5, 5), 10);
        assertEq(target.add(6, 4), 10);

        vm.mockCall(address(target), abi.encodeWithSelector(target.add.selector, 5, 5), abi.encode(11));

        assertEq(target.add(5, 5), 11);
        assertEq(target.add(6, 4), 10);
    }

    function testClearMockedCalls() public {
        Mock target = new Mock();

        vm.mockCall(address(target), abi.encodeWithSelector(target.numberB.selector), abi.encode(10));

        assertEq(target.numberA(), 1);
        assertEq(target.numberB(), 10);

        vm.clearMockedCalls();

        assertEq(target.numberA(), 1);
        assertEq(target.numberB(), 2);
    }

    function testMockCallMultiplePartialMatch() public {
        Mock mock = new Mock();

        vm.mockCall(address(mock), abi.encodeWithSelector(mock.add.selector), abi.encode(10));
        vm.mockCall(address(mock), abi.encodeWithSelector(mock.add.selector, 2), abi.encode(20));
        vm.mockCall(address(mock), abi.encodeWithSelector(mock.add.selector, 2, 3), abi.encode(30));

        assertEq(mock.add(1, 2), 10);
        assertEq(mock.add(2, 2), 20);
        assertEq(mock.add(2, 3), 30);
    }

    function testMockCallWithValue() public {
        Mock mock = new Mock();

        vm.mockCall(address(mock), 10, abi.encodeWithSelector(mock.pay.selector), abi.encode(10));

        assertEq(mock.pay{value: 10}(1), 10);
        assertEq(mock.pay(1), 1);

        for (uint256 i = 0; i < 100; i++) {
            vm.mockCall(address(mock), i, abi.encodeWithSelector(mock.pay.selector), abi.encode(i * 2));
        }

        assertEq(mock.pay(1), 0);
        assertEq(mock.pay{value: 10}(1), 20);
        assertEq(mock.pay{value: 50}(1), 100);
    }

    function testMockCallWithValueCalldataPrecedence() public {
        Mock mock = new Mock();

        vm.mockCall(address(mock), 10, abi.encodeWithSelector(mock.pay.selector), abi.encode(10));
        vm.mockCall(address(mock), abi.encodeWithSelector(mock.pay.selector, 2), abi.encode(2));

        assertEq(mock.pay{value: 10}(1), 10);
        assertEq(mock.pay{value: 10}(2), 2);
        assertEq(mock.pay(2), 2);
    }

    function testMockCallEmptyAccount() public {
        Mock mock = Mock(address(100));

        vm.mockCall(address(mock), abi.encodeWithSelector(mock.add.selector), abi.encode(10));
        vm.mockCall(address(mock), abi.encodeWithSelector(mock.noReturnValue.selector), abi.encode());

        assertEq(mock.add(1, 2), 10);
        mock.noReturnValue();
    }

    function testRevertMock() public {
        Mock mock = new Mock();
        vm.mockCall(address(mock), abi.encodeWithSelector(mock.getRevert.selector), abi.encode(0));

        assertEq(mock.getRevert(), 0);
    }

}

contract MockCallRevertTest is Test {

    error TestError(bytes msg);

    bytes constant ERROR_MESSAGE = "ERROR_MESSAGE";

    function testMockGettersRevert() public {
        Mock target = new Mock();

        // pre-mock
        assertEq(target.numberA(), 1);
        assertEq(target.numberB(), 2);

        vm.mockCallRevert(address(target), abi.encodeWithSelector(target.numberB.selector), ERROR_MESSAGE);

        // post-mock
        assertEq(target.numberA(), 1);
        vm.expectRevert();
        target.numberB();
    }

    function testMockRevertWithCustomError() public {
        Mock target = new Mock();

        assertEq(target.numberA(), 1);
        assertEq(target.numberB(), 2);

        bytes memory customError = abi.encodeWithSelector(TestError.selector, ERROR_MESSAGE);

        vm.mockCallRevert(address(target), abi.encodeWithSelector(target.numberB.selector), customError);

        assertEq(target.numberA(), 1);
        vm.expectRevert(customError);
        target.numberB();
    }

    function testMockNestedRevert() public {
        Mock inner = new Mock();
        NestedMock target = new NestedMock(inner);

        assertEq(target.sum(), 3);

        vm.mockCallRevert(address(inner), abi.encodeWithSelector(inner.numberB.selector), ERROR_MESSAGE);

        vm.expectRevert(ERROR_MESSAGE);
        target.sum();
    }

    function testMockCalldataRevert() public {
        Mock target = new Mock();
        assertEq(target.add(5, 5), 10);
        assertEq(target.add(6, 4), 10);

        vm.mockCallRevert(address(target), abi.encodeWithSelector(target.add.selector, 5, 5), ERROR_MESSAGE);

        assertEq(target.add(6, 4), 10);

        vm.expectRevert(ERROR_MESSAGE);
        target.add(5, 5);
    }

    function testClearMockRevertedCalls() public {
        Mock target = new Mock();

        vm.mockCallRevert(address(target), abi.encodeWithSelector(target.numberB.selector), ERROR_MESSAGE);

        vm.clearMockedCalls();

        assertEq(target.numberA(), 1);
        assertEq(target.numberB(), 2);
    }

    function testMockCallRevertPartialMatch() public {
        Mock mock = new Mock();

        vm.mockCallRevert(address(mock), abi.encodeWithSelector(mock.add.selector, 2), ERROR_MESSAGE);

        assertEq(mock.add(1, 2), 3);

        vm.expectRevert(ERROR_MESSAGE);
        mock.add(2, 3);
    }

    function testMockCallRevertWithValue() public {
        Mock mock = new Mock();

        vm.mockCallRevert(address(mock), 10, abi.encodeWithSelector(mock.pay.selector), ERROR_MESSAGE);

        assertEq(mock.pay(1), 1);
        assertEq(mock.pay(2), 2);

        vm.expectRevert(ERROR_MESSAGE);
        mock.pay{value: 10}(1);
    }

    function testMockCallResetsMockCallRevert() public {
        Mock mock = new Mock();

        vm.mockCallRevert(address(mock), abi.encodeWithSelector(mock.add.selector), ERROR_MESSAGE);

        vm.mockCall(address(mock), abi.encodeWithSelector(mock.add.selector), abi.encode(5));
        assertEq(mock.add(2, 3), 5);
    }

    function testMockCallRevertResetsMockCall() public {
        Mock mock = new Mock();

        vm.mockCall(address(mock), abi.encodeWithSelector(mock.add.selector), abi.encode(5));
        assertEq(mock.add(2, 3), 5);

        vm.mockCallRevert(address(mock), abi.encodeWithSelector(mock.add.selector), ERROR_MESSAGE);

        vm.expectRevert(ERROR_MESSAGE);
        mock.add(2, 3);
    }

    function testMockCallRevertWithCall() public {
        Mock mock = new Mock();

        bytes memory customError = abi.encodeWithSelector(TestError.selector, ERROR_MESSAGE);

        vm.mockCallRevert(address(mock), abi.encodeWithSelector(mock.add.selector), customError);

        (bool success, bytes memory data) = address(mock).call(abi.encodeWithSelector(Mock.add.selector, 2, 3));
        assertEq(success, false);
        assertEq(data, customError);
    }

    function testMockCallEmptyAccount() public {
        Mock mock = Mock(address(100));

        vm.mockCallRevert(address(mock), abi.encodeWithSelector(mock.add.selector), ERROR_MESSAGE);

        vm.expectRevert(ERROR_MESSAGE);
        mock.add(1, 2);
    }
}
