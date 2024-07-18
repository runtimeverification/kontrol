pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "kontrol-cheatcodes/KontrolCheats.sol";

contract MockFunctionContract {
    uint256 public a;

    function mocked_function() public {
        a = 321;
    }

    function mocked_args_function(uint256 x) public {
        a = 321 + x;
    }
}

contract ModelMockFunctionContract {
    uint256 public a;

    function mocked_function() public {
        a = 123;
    }

    function mocked_args_function(uint256 x) public {
        a = 123 + x;
    }
}

contract MockFunctionTest is Test, KontrolCheats {
    MockFunctionContract my_contract;
    ModelMockFunctionContract model_contract;

    function setUp() public {
        my_contract = new MockFunctionContract();
        model_contract = new ModelMockFunctionContract();
    }

    function test_mock_function() public {
        kevm.mockFunction(
            address(my_contract), 
            address(model_contract),
            abi.encodeWithSelector(MockFunctionContract.mocked_function.selector)
        );
        my_contract.mocked_function();
        assertEq(my_contract.a(), 123);
    }

    function test_mock_function_concrete_args() public {
        kevm.mockFunction(
            address(my_contract), 
            address(model_contract),
            abi.encodeWithSelector(MockFunctionContract.mocked_args_function.selector, 456)
        );
        my_contract.mocked_args_function(456);
        assertEq(my_contract.a(), 123 + 456);

        my_contract.mocked_args_function(567);
        assertEq(my_contract.a(), 321 + 567);
    }

    function test_mock_function_all_args() public {
        kevm.mockFunction(
            address(my_contract), 
            address(model_contract),
            abi.encodeWithSelector(MockFunctionContract.mocked_args_function.selector)
        );
        my_contract.mocked_args_function(678);
        assertEq(my_contract.a(), 123 + 678);

        my_contract.mocked_args_function(789);
        assertEq(my_contract.a(), 123 + 789);
    }
}
