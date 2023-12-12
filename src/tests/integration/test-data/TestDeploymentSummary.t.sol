/*  */
/* // SPDX-License-Identifier: UNLICENSED */
/* pragma solidity =0.8.13; */
/*  */
/* import "forge-std/Test.sol"; */
/* import "../src/KEVMCheats.sol"; */
/* import "../src/DeploymentSummary.sol"; */
/*  */
/* contract TestDeploymentSummary is DeploymentSummary { */
/*     function test_deployment_summary() public { */
/*         recreateDeployment(); */
/*     } */
/* } */
/* // SPDX-License-Identifier: UNLICENSED */
pragma solidity =0.8.13;

import "forge-std/Test.sol";
import "../src/KEVMCheats.sol";

contract TestDeploymentSummary is Test, KEVMCheats {

    function test_assert_true() public pure {
        assert(true);
    }
}
