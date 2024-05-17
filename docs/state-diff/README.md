External Computation with Kontrol
=================================
***Injecting Foundry Execution into Proofs***

This folder contains the first iteration for including external computation with Foundry into Kontrol proofs.
To achieve this, there are several files involved and the process has several steps. If you encounter any problems while following what is described here, please reach out in [Discord](https://discord.gg/CurfmXNtbN), we'll be happy to assist!

We use Foundry's [state-diff recording](https://book.getfoundry.sh/cheatcodes/stop-and-return-state-diff) cheatcodes to generate a JSON file that contains all the statte updates that occurred during the recording. We can also produce a JSON file containing the name of the deployed contracts under testing and their addresses.
Using these two JSON files we can (1) name the addresses of the deployed contracts in the Foundry tests and (2) directly add the recorded state updates as the initial state to run the Kontrol proofs.

In short, the steps to add Foundry execution results to Kontrol proofs are the following:

1. Create a fresh Foundry profile to isolate the `src` and `test` folder from the rest of the codebase.
2. Write a contract that uses the provided Solidity files to record the desired execution and execute it with Foundry.
3. Feed the JSON files from the last step to Kontrol to produce the necessary summary contracts for ease of proof writing.
4. Write your symbolic property tests with the right dependencies.
5. Execute Kontrol proofs with the right options to include the recorded computation with Foundry.

# Fresh Foundry Profile

The goal of this step is to create a minimal set of dependencies to run Kontrol proofs while including all the relevant bytecode. That is, we are separating verified bytecode and the sourcecode that produced it. This keeps what is executed by Kontrol to only the essentials, allowing for faster runtimes.

To achieve this separation we'll introduce a new Foundry profile, usually called `kprove`. We also need a fresh folder where the proofs will live. If, for instance, that folder is `test/kontrol/proofs`, the resulting profile would look as follows:
```toml
[profile.kprove]
src = 'test/kontrol/proofs'
out = 'kout-proofs'
test = 'test/kontrol/proofs'
script = 'test/kontrol/proofs'
```

## Special `out` directory

Note that we're also setting a different `out` directory named `kout-proofs`. Because of this, any Kontrol related command will have to be executed in the context of the `kprove` profile. This can be achieved either by `export FOUNDRY_PROFILE=kprove` or by prepending any Kontrol command with that flag (e.g., `FOUNDRY_PROFILE=kprove kontrol list`).
