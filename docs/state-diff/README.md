 🤖⚡ External Computation with Kontrol ⚡🤖
=================================
**Injecting Foundry Execution into Kontrol for Performance and Usability**

This folder is an example of including the results of Foundry execution into the initial state of any proof. This means that Kontrol's proofs will have as their initial state the results from executing any desired code with Foundry. Besides increasing the speed of execution, this considerably improves the user experience for writing proofs about complex protocols.

This project contains all the files and a description of the steps needed to combine Foundry and Kontrol computation successfully. If you need any help with following these instructions, please reach out in [Discord](https://discord.gg/CurfmXNtbN), we'll be happy to assist!

We use Foundry's [state-diff recording](https://book.getfoundry.sh/cheatcodes/stop-and-return-state-diff) cheatcodes to generate a JSON file that contains all the state updates that occurred during the recording. We can also produce a JSON file containing the name of the deployed contracts under testing and their addresses.
Using these two JSON files we can (1) name the addresses of the deployed contracts in the Foundry tests and (2) directly add the recorded state updates as the initial state to run the Kontrol proofs.

In short, the steps to add Foundry execution results to Kontrol proofs are the following:

1. Create a fresh Foundry profile to isolate the `src` and `test` folder from the rest of the codebase.
2. Using the provided Solidity files, write the code that will be executed by Foundry and injected into Kontrol.
3. Tell Kontrol to produce the necessary summary contracts for ease of proof writing.
4. Write your symbolic property tests with the right dependencies.
5. Execute Kontrol proofs with the right options to include the recorded computation with Foundry.

## ✨ Fresh Foundry Profile ✨ 

The goal of this step is to create a minimal set of dependencies to run Kontrol proofs while including all the relevant bytecode. That is, we are separating verified bytecode and the sourcecode that produced it. This keeps what is executed by Kontrol to only the essentials, allowing for faster runtimes.

To achieve this separation we'll introduce a new Foundry profile, usually called `kprove`. We also need a fresh folder where the proofs will live. If, for instance, that folder is `test/kontrol/proofs`, the resulting profile would look as follows:
```toml
[profile.kprove]
src = 'test/kontrol/proofs'
out = 'kout-proofs'
test = 'test/kontrol/proofs'
script = 'test/kontrol/proofs'
```

### ⚠️ Special `out` directory ⚠️

Note that we're also setting a different `out` directory named `kout-proofs`. Because of this, any Kontrol-related command will have to be executed in the context of the `kprove` profile. This can be achieved either by `export FOUNDRY_PROFILE=kprove` or by prepending any Kontrol command with that flag (e.g., `FOUNDRY_PROFILE=kprove kontrol list`).

## 🖋️ Record your execution 🖋️

To record your execution and save its output to a JSON file, simply use the modifier `recordStateDiff` in the [`test/kontrol/state-diff/record-state-diff/RecordStateDiff.sol`](./test/kontrol/state-diff/record-state-diff/RecordStateDiff.sol) file. That is, the initial set up of your proofs has to be run in a function with the `recordStateDiff` modifier. An example of this can be found in [`test/kontrol/state-diff/proof-initialization.sol`](test/kontrol/state-diff/proof-initialization.sol).

On top of that, the `save_address` function allows to save the name of the deployed contract and their addresses into a separate JSON file. This will be crucial to easily write the symbolic property tests later on.

### 🏷️ Name the files 🏷️

There are two different JSON files that can be created, one containing the recorded state updates and another one with the saved names of relevant addresses. Here, a relevant address is any address that will be referenced when writing the proofs. Typically, these are addresses of deployed contracts or priviledged addresses.

On top of that, we have to define in which directory do these files live. For simplicity, we've made it so that these parameters are set with environment variables:
- `STATE_DIFF_NAME`: Name of the JSON containing the state updates. Example: `StateDiff.json`
- `ADDR_NAMES`: Name of the JSON containing the saved names of relevant addresses. Example: `AddressNames.json`
- `STATE_DIFF_DIR`: Path relative to the Foundry root dir where the files will be stored. Example: `state-diff`

### ⭕ Additional permissions ⭕

Before executing the state-recording function you'll need to give Foundry permissions to write the JSON files in the specified directory. To give Foundry write permissions for these files you can add the following to the Foundry profile. Note that the `path` assignment has to be the same as the value set for the `STATE_DIFF_NAME` variable:
```toml
fs_permissions = [
  { access='read-write, path='state-diff' }
]
```
Not adding this would result in a `the path state-diff/StateDiff.json is not allowed to be accessed for write operations` error.

### 🏃 Run the recording 🏃

Run your function containing the initial set up of your proofs (`counterBed` or `counterBedNamed` in our [example](./test/kontrol/state-diff/proof-initialization.sol)) with `forge script state-diff/proof-initialization.sol:CounterBed --sig counterBed --ffi`. Running it with `forge test` will also work, but only if its name starts with `test`. Notice the `--ffi` flag: we use `mkdir` and `touch` to handle the cases where the state diff files don't yet exist.

### 🧼 Clean the State Diff file 🧼

Currently, the produced state diff JSON is escaped when generated. Run the [`clean_json.py`](test/kontrol/scripts/json/clean_json.py) script on the generated state diff file to unescape it. Example: `python3 test/kontrol/scripts/json/clean_json.py state-diff/StateDiff.json`

### 📜 Scripting all of this 📜

Phew! This is nothing short of a mouthful of steps! In case you don't want to manually repeat all that we have gone through, we provide the [`record-state-diff.sh`](test/kontrol/scripts/record-state-diff.sh) script automatically generate the JSON files.
Note that all the relevant environment variables are also present in the script so it can be reused with your project.

## 📝 Write Your Proofs 📝

By now we have generated two files, one containing the recorded state updates of choice and another with the saved names of the relevant addresses. Once we have written the proofs, the state diff JSON will be used by Kontrol to load all the recorded state updates as the initial configuration of the proofs. This means that if we have a test such as the following
```solidity
Counter[] public counters;

function setUp() public {
        for (uint256 i; i <= 9; ++i) {
            counters.push(new Counter());
            counters[i].setNumber(i);
        }
    }

function test_multiple_counters() public {
        for(uint256 i; i <= 9; ++i){
            require(counters[i].number() == i, "Bad number");
        }
    }
```
we can offload the computation of the `setUp` function (of any function, really) to Foundry, and then provide Kontrol with the file containing the state updates that occurred during the execution of `setUp`. Let's see how this transformation is done.

First, we need to run this `setUp` function with the `recordStateDiff` modifier. You can find that function [here](./test/kontrol/state-diff/proof-initialization.sol#L18):
```solidity
function counterBedNamed() public recordStateDiff {
    for (uint256 i; i <= 9; ++i) {
        counter = new Counter();
        counter.setNumber(i);
        save_address(address(counter), string.concat("counter", vm.toString(i)));
    }
}
```
Notice that we're saving the addresses via `save_address`, not via the `Counter[]`. 

The next step is to use Kontrol's `load-state-diff` command. An example on how to use it can be found in [the provided script](test/kontrol/scripts/record-state-diff.sh). For our running example it can be called as follows:
```
kontrol load-state-diff InitialState state-diff/StateDiff.json --contract-names state-diff/AddressNames.json --output-dir test/kontrol/proofs/utils
```
This will
- Create two contracts, [`InitialState.sol`](test/kontrol/proofs/utils/InitialState.sol) and [`InitialStateCode.sol`](test/kontrol/proofs/utils/InitialStateCode.sol)
  - `InitialState.sol` will have the names of the addresses from `AddressNames.json` and a function `recreateDeployment` that uses `vm.etch` and `vm.store` to allow for state-recreation.
  - `InitialStateCode.sol` contains the code for the relevant addresses used in `InitialState.sol`.
- Save the two contracts in the directory indicated to the `--output-dir` flag.

The relevant part for writing our tests is that `InitialState.sol` contains the following address names:
```solidity
address internal constant counter8Address = 0x03A6a84cD762D9707A21605b548aaaB891562aAb;
address internal constant counter6Address = 0x1d1499e622D69689cdf9004d05Ec547d650Ff211;
address internal constant counter1Address = 0x2e234DAe75C793f67A35089C9d99245E1C58470b;
address internal constant counter0Address = 0x5615dEB798BB3E4dFa0139dFa1b3D433Cc23b72f;
address internal constant counter3Address = 0x5991A2dF15A8F6A256D3Ec51E99254Cd3fb576A9;
address internal constant counter7Address = 0xA4AD4f68d0b91CFD19687c881e50f3A00242828c;
address internal constant counter9Address = 0xD6BbDE9174b1CdAa358d2Cf4D57D1a9F7178FBfF;
address internal constant counter2Address = 0xF62849F9A0B5Bf2913b396098F7c7019b51A820a;
address internal constant counter5Address = 0xa0Cb889707d426A7A386870A03bc70d1b0697598;
address internal constant counter4Address = 0xc7183455a4C133Ae270771860664b6B7ec320bB1;
```
This means that we'll make [our test](test/kontrol/proofs/Counter.k.sol) inherit `InitialState.sol` and add the necessary interface to each address:
```solidity
Counter[] public counters;

function setUp() public {
    counters.push(Counter(address(counter0Address)));
    counters.push(Counter(address(counter1Address)));
    counters.push(Counter(address(counter2Address)));
    counters.push(Counter(address(counter3Address)));
    counters.push(Counter(address(counter4Address)));
    counters.push(Counter(address(counter5Address)));
    counters.push(Counter(address(counter6Address)));
    counters.push(Counter(address(counter7Address)));
    counters.push(Counter(address(counter8Address)));
    counters.push(Counter(address(counter9Address)));
}
```
Note that in the previous `setUp` we were deploying contracts + calling `setNumber` on each contract and storing them in the `Counters[]` array. Here we're only casting the addresses with the right interface and storing them in `counters`.

**A note on interfaces**: One of the goals of this technique is to isolate the verified bytecode from the source code producing it. Therefore `Counter` here is just an interface of the actual `Counter` contract. The interface can be found [here](test/kontrol/proofs/utils/Interfaces.sol). To see more clearly how this is brought together, see the test [here](test/kontrol/proofs/Counter.k.sol).

Note that [our test](test/kontrol/proofs/Counter.k.sol) is named `prove_multiple_counters`. The reason for not using `test_` is that, since we're not including the `recreateDeployment` function in the `setUp`, running that test with `forge` will not be successful, since the state updates haven't been loaded.

However, we don't need to run the `recreateDeployment` function in Kontrol! Let's see how we can execute `prove_multiple_counters`.

## ⚙️ Run Your Proofs ⚙️

At this point we have a test that says things about addresses, but no information about the addresses is actually present in the contract! That is, we have following `setUp` function that just stores the addresses to which `counterBedNamed` deployed bytecode to. Note that these addresses were saved through the `save_address` function to the `state-diff/AddressNames.json`, and that `kontrol load-state-diff` appends `Address` to the specified name. You can see the [automatically generated file](test/kontrol/proofs/utils/InitialState.sol) for more details.
```solidity
Counter[] public counters;

function setUp() public {
    counters.push(Counter(address(counter0Address)));
    counters.push(Counter(address(counter1Address)));
    counters.push(Counter(address(counter2Address)));
    counters.push(Counter(address(counter3Address)));
    counters.push(Counter(address(counter4Address)));
    counters.push(Counter(address(counter5Address)));
    counters.push(Counter(address(counter6Address)));
    counters.push(Counter(address(counter7Address)));
    counters.push(Counter(address(counter8Address)));
    counters.push(Counter(address(counter9Address)));
}
```
And the following test that asserts some property of each of the stored addresses:
```solidity
function prove_multiple_counters() public {
        for(uint256 i; i <= 9; ++i){
            require(counters[i].number() == i, "Bad number");
        }
    }
```
As mentioned above, from the code's perspective, these are empty addresses! So we need to tell Kontrol which state updates need to be loaded before executing `prove_multiple_counters`.
This is done via the `--init-node-from` flag of the `kontrol prove` command. The `--init-node-from` flag expects a JSON file containing the state updates and will load them to the initial state of the proof. This will make Kontrol aware of all the changes that occurred during the execution of the original `setUp` function, with none of the computation.

Hence, to successfully execute the above function in Kontrol we'll have to execute:
1. `FOUNDRY_PROFILE=kprove kontrol build`
2. `FOUNDRY_PROFILE=kprove kontrol prove --match-test prove_multiple_counters --init-node-from state-diff/StateDiff.json`
Note that running this in the context of the `kprove` profile is crucial, since it points to the isolated folder that will contain all the necessary bytecode.

By successfully follwoing all these steps, you should be greeted with the following message 🙂

```
PROOF PASSED: test%kontrol%proofs%CounterKontrol.prove_multiple_counters():0
```
