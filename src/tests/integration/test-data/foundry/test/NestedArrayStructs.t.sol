// SPDX-License-Identifier: UNLICENSED
pragma solidity =0.8.13;

import "forge-std/Test.sol";

interface ProjectConfig {
    struct ChainEnv {
        string chainName;
        string chainIndex;
    }

    struct Vault {
        string tokenName;
        address oracle;
        uint256 allowedToTrade;
        InputData params;
        uint256 reserves;
    }

    struct InputData {
        uint256 ltv;
        uint256 rate;
        uint256 exchangeRate;
        uint256 utilization;
    }

    struct AssetAddresses {
        address cToken;
        address dToken;
    }

    struct VaultWithAddresses {
        Vault vault;
        AssetAddresses addresses;
    }
}

contract NestedStructArrayTest is Test, ProjectConfig {
    function testListAssetsCustom(ChainEnv calldata environment, VaultWithAddresses[] memory listings) external { 
        assert(listings.length == 1);
    }
}