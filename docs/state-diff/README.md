 🤖⚡ External Computation with Kontrol ⚡🤖
=================================
**Injecting Foundry Execution into Proofs**

This folder is an example for including external computation with Foundry into Kontrol proofs.
To achieve this, there are several files involved and the process has several steps. If you encounter any problems while following what is described here, please reach out in [Discord](https://discord.gg/CurfmXNtbN), we'll be happy to assist!

We use Foundry's [state-diff recording](https://book.getfoundry.sh/cheatcodes/stop-and-return-state-diff) cheatcodes to generate a JSON file that contains all the state updates that occurred during the recording. We can also produce a JSON file containing the name of the deployed contracts under testing and their addresses.
Using these two JSON files we can (1) name the addresses of the deployed contracts in the Foundry tests and (2) directly add the recorded state updates as the initial state to run the Kontrol proofs.

In short, the steps to add Foundry execution results to Kontrol proofs are the following:

1. Create a fresh Foundry profile to isolate the `src` and `test` folder from the rest of the codebase.
2. Write a contract that uses the provided Solidity files to record the desired execution and execute it with Foundry.
3. Feed the JSON files from the last step to Kontrol to produce the necessary summary contracts for ease of proof writing.
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

### ⚠️  Special `out` directory ⚠️

Note that we're also setting a different `out` directory named `kout-proofs`. Because of this, any Kontrol related command will have to be executed in the context of the `kprove` profile. This can be achieved either by `export FOUNDRY_PROFILE=kprove` or by prepending any Kontrol command with that flag (e.g., `FOUNDRY_PROFILE=kprove kontrol list`).

## 🖋️ Record your execution 🖋️

To record your execution and save its output to a JSON file, simply use the modifier `recordStateDiff` in the [`test/kontrol/state-diff/record-state-diff/RecordStateDiff.sol`](./test/kontrol/state-diff/record-state-diff/RecordStateDiff.sol) file. That is, the initial set up of your proofs has to be run in a function with the `recordStateDiff` modifier. An example of this can be found in [`test/kontrol/state-diff/proof-initialization.sol`](test/kontrol/state-diff/proof-initialization.sol).

On top of that, the `save_address` function allows to save the name of the deployed contract and their addresses into a separate JSON file. This will be crucial to easily write the symbolic property tests later on.

### 🏷️ Name the files 🏷️

There are two different JSON files that can be created, one containing the recorded state updates and another one with the saved names of important addresses. On top of that, we have to define in which directory do these files live. For simplicity, we've made it so that these parameters are set with environment variables:
- `STATE_DIFF_NAME`: Name of the JSON containing the state updates. Example: `StateDiff.json`
- `ADDR_NAMES`: Name of the JSON containing the saved names of relevant addresses. Example: `AddressNames.json`
- `STATE_DIFF_FOLDER`: Path relative to the foundry root dir where the files will be stored. Example: `state-diff`

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


