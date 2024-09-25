// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

contract NestedStructsTest is Test {
    struct Processor {
        Window windows;
    }

    struct Window {
        Frame[] frames;
        bytes32 hash;
    }

    struct Frame {
        Pointer position;
        bytes32 root;
    }

    struct Pointer {
        PointerType pointerType;
        uint256 value;
    }

    enum PointerType {
        INT32,
        INT64
    }

    function prove_fourfold_nested_struct(Processor calldata initialProcessor) external pure {
        assert(initialProcessor.windows.frames.length == 1);
    }

    function prove_fourfold_nested_struct_array(Processor[] calldata initialProcessor) external pure {
        assert(initialProcessor[0].windows.frames.length == 1);
    }
}
