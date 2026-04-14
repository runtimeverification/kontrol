# Kontrol — Claude Code Guide

## Project overview

Kontrol is a formal verification tool that combines KEVM (K Semantics of the EVM) with Foundry to allow developers to perform symbolic execution and formal verification of Solidity smart contracts without learning a new language.
It is implemented as a Python package (`kontrol`) with K semantic definitions.

- **Version**: placeholder `1.0.0` on master — real versions (e.g. `1.0.236`) are managed via `package/version` + `package/version.sh version_sub` and committed on the release branch
- **Entry point**: `kontrol` CLI (`kontrol.__main__:main`)
- **Python**: ~3.10+
- **Build backend**: hatchling

---

## `src/kontrol/` — Core Python Package

```
src/kontrol/
├── __init__.py                  # Package version declaration (VERSION = '1.0.0' placeholder on master; patched per-release)
├── __main__.py                  # CLI entry point; dispatches exec_* commands
├── cli.py                       # Argument parser; maps CLI commands to option objects
├── options.py                   # Dataclass-style options for every CLI subcommand
├── foundry.py                   # Core: Foundry class, KontrolSemantics, proof management
├── prove.py                     # foundry_prove(): symbolic proof execution engine
├── kompile.py                   # foundry_kompile(): builds the K definition from contracts
├── solc_to_k.py                 # Translates Solidity ABI/AST into K terms (Contract, Input)
├── solc.py                      # Parses Solidity compiler output (bytecode, source maps)
├── natspec.py                   # Parses NatSpec @custom:kontrol annotations into K preconditions
├── display.py                   # foundry_show() and foundry_view() for proof visualization
├── counterexample_generation.py # Generates Forge Solidity repro tests from failed proofs
├── storage_generation.py        # Generates symbolic storage constants for contracts
├── state_record.py              # Loads recorded Foundry state diffs/dumps into K account cells
└── utils.py                     # Shared utilities: logging, file I/O, version checks
```

| Module                         | Key Exports                                                 | Purpose                                                                        |
| ------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `foundry.py`                   | `Foundry`, `KontrolSemantics`, `FoundryKEVM`                | Central proof state, custom EVM steps (ffi, rename, forgetBranch, console.log) |
| `prove.py`                     | `foundry_prove()`                                           | Runs APR proofs in parallel with `multiprocess`                                |
| `kompile.py`                   | `foundry_kompile()`                                         | Compiles Solidity → K module for the prover                                    |
| `solc_to_k.py`                 | `Contract`, `Input`, `StorageField`                         | ABI-to-K translation layer                                                     |
| `natspec.py`                   | `apply_natspec_preconditions()`                             | Parses Solidity NatSpec into K ML constraints                                  |
| `counterexample_generation.py` | `ParsedTestId`, `generate_counterexample_test()`            | Extracts concrete values from failed proofs                                    |
| `state_record.py`              | `foundry_state_load()`, `recorded_state_to_account_cells()` | Injects Foundry execution state into proofs                                    |
| `cli.py`                       | `generate_options()`, `_create_argument_parser()`           | Wires CLI args to typed option objects                                         |
| `options.py`                   | `ProveOptions`, `BuildOptions`, `ShowOptions`, …            | Typed options for all 20+ CLI subcommands                                      |

---

## `src/kontrol/kdist/` — K Semantic Definitions

K Markdown (literate K) files compiled by `kdist` into the Haskell backend prover.
Also contains the `kdist` plugin registration.

```
src/kontrol/kdist/
├── plugin.py               # Registers build targets: base, keccak, aux, full
├── kontrol.md              # Top-level K module composition (KONTROL-BASE/AUX/KECCAK/FULL)
├── foundry.md              # FOUNDRY module: configuration, success predicate, accounts
├── cheatcodes.md           # FOUNDRY-CHEAT-CODES: prank, expectRevert, expectEmit, mockCalls, whitelist
├── assert.md               # KONTROL-ASSERTIONS: #assert cheatcode implementation
├── hevm.md                 # HEVM-SUCCESS: hevm-compatible success predicate
├── keccak.md               # KECCAK-LEMMAS: keccak range and simplification lemmas
├── kontrol_lemmas.md       # KONTROL-AUX-LEMMAS: arithmetic and map simplification lemmas
├── no_stack_checks.md      # NO-STACK-CHECKS: optimized EVM rules skipping stack overflow checks
└── no_code_size_checks.md  # NO-CODE-SIZE-CHECKS: disables EIP-170 code size limit for test contracts
```

| Target           | K Module         | Includes                                        |
| ---------------- | ---------------- | ----------------------------------------------- |
| `kontrol.base`   | `KONTROL-BASE`   | FOUNDRY + NO-STACK-CHECKS + NO-CODE-SIZE-CHECKS |
| `kontrol.aux`    | `KONTROL-AUX`    | base + KONTROL-AUX-LEMMAS                       |
| `kontrol.keccak` | `KONTROL-KECCAK` | base + KECCAK-LEMMAS                            |
| `kontrol.full`   | `KONTROL-FULL`   | aux + keccak (everything)                       |

---

## `src/tests/` — Test Suite

```
src/tests/
├── unit/                        # Fast, dependency-free unit tests
├── integration/                 # Full end-to-end prove/build tests (requires compiled kdist)
│   ├── conftest.py              # Module fixtures: foundry (compiled), server (kore-rpc-booster)
│   ├── test_foundry_prove.py    # Main integration suite (prove, show, refute, split, merge, etc.)
│   ├── test_hevm_prove.py       # hevm-mode symbolic proof tests
│   ├── test_kontrol.py          # End-to-end suite: bootstraps a real project via kontrol init, then builds and proves
│   ├── test_kontrol_cse.py      # Compositional Symbolic Execution (CSE/summary) tests
│   └── test-data/
│       ├── foundry/             # Foundry project for the main integration suite
│       ├── src/                 # Solidity sources copied into the end-to-end project (e.g. SimpleStorage.sol)
│       ├── test/                # Solidity tests copied into the end-to-end project (cheatcodes, etc.)
│       └── show/                # Expected `kontrol show` output snapshots (.expected files)
└── profiling/                   # Performance profiling tests
```

---

## `scripts/` — Developer Scripts

| Script             | Purpose                                                                                                                   |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `build-kontrol`    | Full build: K version check/install, `uv sync`, `kdist clean+build`. |
| `selector "<sig>"` | Compute the ABI function selector for `<sig>` as a decimal integer (uses `cast sig`).                                     |
| `update-expected-output [--foundry] [--cse] [--end-to-end] [-k <filter>]` | Wrapper script over the make recipes to egenerate expected-output snapshots. Pass a suite flag to target one suite; `-k` scopes to a single test. Runs all suites if no flag given. |

---

## CLI Commands (from `__main__.py`)

| Command                  | Handler                            | Description                             |
| ------------------------ | ---------------------------------- | --------------------------------------- |
| `kontrol version`        | `exec_version`                     | Print version                           |
| `kontrol build`          | `exec_build` → `foundry_kompile()` | Compile Solidity + K definition         |
| `kontrol prove`          | `exec_prove` → `foundry_prove()`   | Run symbolic proofs                     |
| `kontrol show`           | `exec_show` → `foundry_show()`     | Display KCFG of a proof                 |
| `kontrol list`           | `exec_list` → `foundry_list()`     | List all proofs and their status        |
| `kontrol view-kcfg`      | `exec_view_kcfg`                   | TUI viewer for KCFG                     |
| `kontrol load-state`     | `exec_load_state`                  | Load Foundry recorded state into proofs |
| `kontrol init`           | `exec_init` → `init_project()`     | Scaffold a new Kontrol project          |
| `kontrol refute-node`    | `exec_refute_node`                 | Mark a node as refuted                  |
| `kontrol unrefute-node`  | `exec_unrefute_node`               | Unmark a refuted node                   |
| `kontrol split-node`     | `exec_split_node`                  | Split a node on a condition             |
| `kontrol merge-nodes`    | `exec_merge_nodes`                 | Merge proof nodes                       |
| `kontrol step-node`      | `exec_step_node`                   | Step execution at a node                |
| `kontrol simplify-node`  | `exec_simplify_node`               | Simplify a node's term                  |
| `kontrol remove-node`    | `exec_remove_node`                 | Remove a node from KCFG                 |
| `kontrol section-edge`   | `exec_section_edge`                | Bisect a KCFG edge                      |
| `kontrol get-model`      | `exec_get_model`                   | Query SMT model for a node              |
| `kontrol minimize-proof` | `exec_minimize_proof`              | Minimize proof KCFG                     |
| `kontrol clean`          | `exec_clean`                       | Remove proof artifacts                  |
| `kontrol setup-storage`  | `exec_setup_storage`               | Generate storage constants              |

---

## Dependency Overview

- **`kevm-pyk`** (from `evm-semantics`): KEVM Python bindings, `KEVM` class, `KEVMSemantics`
- **`pyk`**: K Framework Python API — `KCFG`, `APRProof`, `CTerm`, `kdist`, `KoreClient`
- **`eth-abi`**, **`eth-utils`**: Ethereum ABI encoding/decoding
- **`pycryptodome`**: Cryptographic primitives
- **`pyevmasm`**: EVM bytecode disassembly (used in `solc.py`)
- **`openzeppelin-solidity-grammar-parser`** (`sgp`): Solidity expression parser for NatSpec
- **`tomlkit`**: TOML parsing for `foundry.toml`
- **`rich`**: Console output formatting

---

## Development Workflow

```bash
# 1. Build 
# Recommendation: use the /build skill.
# Required when: K semantic files changed (src/kontrol/kdist/), first-time setup, or K version upgrade.
# Not required for Python-only changes (foundry.py, prove.py, etc.).

# 2. After any Python change: format then run all checkers + unit tests
make format   # auto-format (autoflake + isort + black)
make          # check (flake8, mypy, autoflake, isort, black) + unit tests

# 3. Tests
make test-unit          # Fast, no kdist required
make test-integration   # Full end-to-end, requires built kdist
make profile            # Performance profiling

# 4. Update expected output snapshots
# Use the /update-expected-output skill.
```

---

## Code style

- Formatter: `black` (line length 120, no string normalization)
- Import sorter: `isort` (black profile, line_length 120)
- Linter: `flake8` with bugbear, comprehensions, quotes, type-checking plugins
- Type checker: `mypy` with `disallow_untyped_defs = true`
- All formatting/lint tools run via `uv run <tool>`
- `src/tests/integration/test-data` is excluded from autoflake and mypy

---

## Testing conventions

Integration tests are split into two fixture worlds that must not be mixed:

| Suite (`-k` filter)                   | Test file               | Fixtures / Foundry project       | CI lists                                                                     |
| ------------------------------------- | ----------------------- | -------------------------------- | ---------------------------------------------------------------------------- |
| `test_foundry_prove`                  | `test_foundry_prove.py` | `test-data/foundry/`             | `foundry-prove-all`, `foundry-prove-skip`, `foundry-fail`, `foundry-bmc-all` |
| `test_foundry_minimize_proof`         | `test_foundry_prove.py` | `test-data/foundry/`             | `foundry-minimize`                                                           |
| `test_kontrol_cse` (file-level match) | `test_kontrol_cse.py`   | `test-data/foundry/`             | `foundry-dependency-all`                                                     |
| `test_kontrol_end_to_end`             | `test_kontrol.py`       | fresh project via `kontrol init` | `end-to-end-prove-all`, `end-to-end-prove-skip`                              |

The `test_kontrol_end_to_end` fixture creates a real Kontrol project from scratch: it calls `kontrol init`, copies `test-data/src/` and `test-data/test/` into the project, then runs `kontrol build` to compile it.
Tests then run `kontrol prove` against that compiled project.

**New cheatcode tests** go in `test-data/test/` and are registered in `end-to-end-prove-all` — they run under `test_kontrol_end_to_end`, not `test_foundry_prove`.

Run a specific suite scoped to one test:

```bash
make test-integration TEST_ARGS="-k 'test_kontrol_end_to_end and <TestClass>'"
make test-integration TEST_ARGS="-k 'test_foundry_prove and <TestClass>'"
```

Pass `--update-expected-output` via `TEST_ARGS` to regenerate expected outputs.

---

## Cheatcodes: Foundry vs Kontrol-proprietary

All cheatcodes (both Foundry and Kontrol-proprietary) are implemented in `src/kontrol/kdist/cheatcodes.md` (module `FOUNDRY-CHEAT-CODES`) and `src/kontrol/kdist/assert.md` (module `KONTROL-ASSERTIONS`).
They are all dispatched via the same Foundry cheatcode address (`0x7109709ecfa91a80626ff3989d68f67f5b1dd12d`), using ABI function selectors.

### Foundry cheatcodes (standard `vm.*`)

These match Foundry's `Vm` interface.
Kontrol implements them to make existing Foundry test suites runnable under symbolic execution without changes.

| Cheatcode                            | Purpose                                                                                                                                                                                                |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `assume(bool)`                       | Inject a path constraint — **semantics differ from Foundry**: in Foundry fuzz testing it discards the fuzz input; in Kontrol it adds the condition as a hard constraint on the symbolic execution path |
| `deal(address, uint256)`             | Set an account's ETH balance                                                                                                                                                                           |
| `etch(address, bytes)`               | Set an account's bytecode                                                                                                                                                                              |
| `warp(uint256)`                      | Set block timestamp                                                                                                                                                                                    |
| `roll(uint256)`                      | Set block number                                                                                                                                                                                       |
| `fee(uint256)`                       | Set block base fee                                                                                                                                                                                     |
| `chainId(uint256)`                   | Set chain ID                                                                                                                                                                                           |
| `coinbase(address)`                  | Set block coinbase                                                                                                                                                                                     |
| `load` / `store`                     | Read/write storage slots directly                                                                                                                                                                      |
| `getNonce` / `setNonce`              | Get/set account nonce                                                                                                                                                                                  |
| `computeCreateAddress(address,uint256)` | Predict the address a contract will be deployed to via CREATE, given deployer address and nonce                                                                                                     |
| `addr(uint256)`                      | Derive address from private key                                                                                                                                                                        |
| `label(address, string)`             | Attach a human-readable label to an address                                                                                                                                                            |
| `sign(uint256, bytes32)`             | Sign a digest with a private key                                                                                                                                                                       |
| `prank` / `startPrank` / `stopPrank` | Impersonate `msg.sender` and `tx.origin` for calls                                                                                                                                                     |
| `expectRevert`                       | Assert the next call reverts (with optional reason)                                                                                                                                                    |
| `expectEmit`                         | Assert a specific event is emitted                                                                                                                                                                     |
| `expectCall` variants                | Assert a specific call type occurs (`CALL`, `STATICCALL`, `DELEGATECALL`, `CREATE`, `CREATE2`)                                                                                                         |
| `mockCall`                           | Return fixed data for calls to a given address/calldata                                                                                                                                                |
| `mockFunction`                       | Replace a function implementation with a mock                                                                                                                                                          |
| `ffi(string[])`                      | Execute a shell command — in symbolic mode returns a fresh symbolic variable unless `--ffi` is passed                                                                                                  |
| `setArbitraryStorage(address)`       | Make an account's storage fully symbolic (Foundry's name for what Kontrol originally called `symbolicStorage`)                                                                                         |
| `toString(...)`                      | Convert various types to their hex string representation                                                                                                                                               |
| `assert*` family                     | `assertEq`, `assertNotEq`, `assertTrue`, `assertFalse`, `assertGe`, `assertGt`, `assertLe`, `assertLt`, `assertApproxEqAbs`, `assertApproxEqRel` — implemented in `assert.md`                          |

### Kontrol-proprietary cheatcodes

These have no equivalent in standard Foundry.
They exist to expose symbolic execution primitives directly to Solidity test code.

| Cheatcode                                                       | Purpose                                                                                                                                                                     |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `freshUInt(uint8)` / `freshUInt(uint8, string)`                 | Return a fresh symbolic `uint` of the given bit width (1–256 bits). The `string` variant names the symbolic variable for readable counterexamples.                          |
| `freshBool()` / `freshBool(string)`                             | Return a fresh symbolic `bool` (unconstrained 0 or 1)                                                                                                                       |
| `freshBytes(uint256)` / `freshBytes(uint256, string)`           | Return a fresh symbolic `bytes` of the given length                                                                                                                         |
| `freshAddress()` / `freshAddress(string)`                       | Return a fresh symbolic `address` (guaranteed ≠ test/cheat addresses)                                                                                                       |
| `symbolicStorage(address)` / `symbolicStorage(address, string)` | Make an account's storage fully symbolic — Kontrol's original name, kept as an alias for `setArbitraryStorage`. The `string` variant names the storage for counterexamples. |
| `copyStorage(address, address)`                                 | Copy the storage of one account into another — useful for setting up proof state                                                                                            |
| `forgetBranch(uint256, uint8, uint256)`                         | Remove a path constraint from the current branch — allows collapsing proof branches that diverge on a condition you want to abstract away                                   |
| `setGas(uint256)`                                               | Set the gas counter to a concrete value — used when a test depends on specific gas amounts                                                                                  |
| `infiniteGas()`                                                 | Reset gas to a fresh symbolic value — effectively infinite gas, the default during proving                                                                                  |

### Key semantic distinctions

- **`random*` vs `fresh*`**: Foundry added `randomUint()`, `randomBool()`, `randomBytes()`, `randomAddress()` as pseudo-random runtime values.
  Kontrol treats them identically to the `fresh*` variants — both produce unconstrained symbolic variables.
  There is no randomness at the prover level.
- **`assume`**: In Foundry fuzz testing, `vm.assume(cond)` causes the fuzzer to skip that input if `cond` is false.
  In Kontrol, it injects `cond` as a hard path constraint — it restricts the symbolic state space rather than filtering inputs.
- **`ffi`**: In Foundry, always executes the shell command.
  In Kontrol without `--ffi`, returns a fresh symbolic variable instead of running the command, allowing proofs to proceed over unknown external outputs.

---

## Gotchas

- **Any change to `kdist/` requires a full rebuild**. Use the `/build` skill before running the prover.
  There is no incremental build within a target.
- **`src/tests/integration/test-data` is excluded from `autoflake` and `mypy`**. Lint errors there are expected and will not fail `make check`.
- **Integration tests require a pre-built kdist**.
  Running `make test-integration` without a built distribution will fail with a missing artifact error, not a helpful message.
- **`make test` runs all tests including integration**. Use `make test-unit` for fast feedback during development.
- **The `multiprocess` library** (not `multiprocessing`) is used in `prove.py` for parallel proof execution.
  They have different APIs; don't confuse them.
- **`tomlkit` preserves TOML formatting on round-trip**. This is intentional in `foundry.py`.
  Don't swap it for a plain TOML parser.
- **`kore-rpc-booster` processes might be left hanging after integration test runs**. Always run `pkill -9 -f "kore-rpc-booster"` after snapshot update runs, otherwise the process stays alive and interferes with subsequent test runs.
