pragma solidity =0.8.13;

import "forge-std/Test.sol";

import "kontrol-cheatcodes/KontrolCheats.sol";

contract MockFunctionContract {
    uint256 public a;

    function mocked_function() public {
        a = 321;
    }
}

contract ModelMockFunctionContract {
    uint256 public a;

    function mocked_function() public {
        a = 123;
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
}
