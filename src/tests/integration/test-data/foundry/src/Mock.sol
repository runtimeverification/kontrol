pragma solidity =0.8.13;

contract Mock {
    uint256 state = 0;

    function numberA() public pure returns (uint256) {
        return 1;
    }

    function numberB() public pure returns (uint256) {
        return 2;
    }

    function add(uint256 a, uint256 b) public pure returns (uint256) {
        return a + b;
    }

    function pay(uint256 a) public payable returns (uint256) {
        return a;
    }

    function noReturnValue() public {
        // Does nothing of value, but also ensures that Solidity will 100%
        // generate an `extcodesize` check.
        state += 1;
    }

    function getRevert() public view returns (uint256) {
        require(varTest != 0, "Var test is 0");
        return varTest;
    }
}

contract NestedMock {
    Mock private inner;

    constructor(Mock _inner) {
        inner = _inner;
    }

    function sum() public view returns (uint256) {
        return inner.numberA() + inner.numberB();
    }
}