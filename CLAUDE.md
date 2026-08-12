# Kontrol — Project Conventions

Kontrol is the Foundry integration for KEVM: it compiles a Foundry project's Solidity into K and runs symbolic-execution proofs over its `test*` functions.
It is a thin Python layer (`src/kontrol/`) on top of two upstream dependencies — `kevm-pyk` (the EVM semantics + K frontend) and `pyk` (K's Python toolkit: option system, proof/KCFG infrastructure, RPC clients).
Most of the heavy lifting lives upstream; Kontrol adds Foundry-specific semantics (cheatcodes, storage layout), the CLI, and the proof orchestration.

## Architecture: the `src/kontrol` package

The package is small; each module has a clear role:

- `__main__.py` — entry point.
  `main()` parses args, builds the typed options object, then dispatches by convention: command `foo-bar` runs the `exec_foo_bar()` function in this module.
  Each `exec_*` loads a `Foundry` object and delegates to a `foundry_*` domain function.
- `cli.py` — `KontrolCLIArgs` (subclass of `kevm_pyk`'s `KEVMCLIArgs`) and `_create_argument_parser()` build the argparse tree; `generate_options()` maps parsed args to the right Options class.
- `options.py` — one `Options` dataclass per command (`ProveOptions`, `ShowOptions`, `BuildOptions`, …) plus shared mixins like `RpcOptions`.
  This is the load-bearing pattern: each class defines `default()`, `from_option_string()`, and `get_argument_type()` static methods, and pyk's `Options.__init__` walks the MRO to merge defaults from every parent with TOML config and CLI args by field name.
  Because the same option can arrive from a CLI flag, a `kontrol.toml` key, or a default, **a new flag must be wired in all three places** — the argparse arg in `cli.py`, the field + `default()` entry in `options.py`, and (if its CLI name differs from the field) `from_option_string()`/`get_argument_type()`.
- `foundry.py` — the `Foundry` class (wraps a project root, `foundry.toml`, the `KEVM` instance, and the `out/` artifacts) plus every `foundry_*` domain function for the non-prove commands.
  `FoundryKEVM(KEVM)` and `KontrolSemantics(KEVMSemantics)` live here; `KontrolSemantics` is where Foundry cheatcodes (FFI, `console.log`, symbolic-storage helpers) are handled as custom KCFG steps.
- `prove.py` — `foundry_prove()` orchestrates proofs: spins up the Kore/Booster RPC server, builds the test list from `--match-test`, and for each test drives a `pyk` `KCFGExplore` (over a `CTermSymbolic` RPC client) to extend the KCFG to completion.
- `display.py` — `foundry_show()` / `foundry_view()` render a proof's KCFG as text or in the interactive TUI.
- `kompile.py` — `foundry_kompile()` generates `foundry.k` from solc output and calls into `kevm_pyk`'s kompile.
- `solc_to_k.py` — parses solc JSON output into a `Contract` model and emits the per-contract K.
- `kdist/` — the K semantics Kontrol owns: `kontrol.md` (entry), `cheatcodes.md`, `foundry.md`, `assert.md`, `kontrol_lemmas.md`, etc., compiled via the kdist plugin (see below).

The dependency boundary: EVM-layer semantics and lemmas live **upstream** in `evm-semantics`/`kevm-pyk` (pinned by the `kevm-pyk@git+…@vX.Y.Z` ref in `pyproject.toml`); only Foundry-specific semantics live in `src/kontrol/kdist/`.
A change needed in the EVM layer is an upstream change — see the cross-repo rules.

## Development environment & checks

`uv` is the package manager (version pinned in `deps/uv_release`); Python `~=3.10`.
`uv sync` installs the dev dependency group; every tool runs under `uv run`.
The Makefile is the source of truth for how to invoke everything (`UV_RUN := uv run --`).

Code-quality workflow before any PR — `make format` then `make check`:

- `make format` = `autoflake` (remove unused imports/vars, in place) → `isort` → `black`, all over `src`.
- `make check` = `check-flake8 check-mypy check-autoflake check-isort check-black` — the read-only counterparts; this is exactly what CI's Code Quality job runs, plus `make pyupgrade`.
- Tool configs: `.flake8` (line length 120, bugbear + strict type-checking + quotes + pep8-naming plugins, `__init__.py` exempt from F401, `test-data` excluded); `pyproject.toml` for mypy (`disallow_untyped_defs = true`), isort (`profile = black`), black (line length 120, `skip-string-normalization`), and autoflake.
- `make pyupgrade` (`--py310-plus`) is optional, not part of `make check`, but CI runs it as a separate step.

Note: `black --check` prints a Python-3.10-vs-target-version parse warning on this machine; it is harmless and the files still pass.

## Claude Code skills

`.claude/skills/` ships repo-specific skills that automate the workflows described in this guide; invoke them by name in Claude Code:

- **`/build`** — full K build. Wraps `scripts/build-kontrol` (K version check/install, `uv sync`, `kdist clean`, `kdist build`). Use whenever `src/kontrol/kdist/` changed, on first setup, or after a K version bump.
- **`/add-cheatcode <signature>`** — add a Foundry or Kontrol-proprietary cheatcode end to end (K rule in `cheatcodes.md`, selector, subconfig, Solidity test, CI-list registration, rebuild).
- **`/update-expected-output`** — regenerate `show` golden files for the integration suites. Wraps `scripts/update-expected-output`; scope it to a suite or a single `-k` test and run it in the background (it is slow).
- **`/writing-kontrol-lemmas`** — author and validate K simplification lemmas when `kontrol prove` leaves pending/stuck KCFG leaves, using a stand-alone `runLemma`/`doneLemma` harness rather than the full Solidity build.

## Building the K definition (kdist)

Kontrol's K semantics are compiled through pyk's kdist system; targets are declared in `src/kontrol/kdist/plugin.py` (registered via the `[project.entry-points.kdist] kontrol = "kontrol.kdist.plugin"` entry point).
Four Haskell-backend targets, all rooted at `kontrol.md`, differ only by which lemmas the main module pulls in:

- `kontrol.base` → module `KONTROL-BASE` (no extra lemmas).
- `kontrol.keccak` → `KONTROL-KECCAK` (Keccak assumptions).
- `kontrol.aux` → `KONTROL-AUX` (auxiliary helper lemmas).
- `kontrol.full` → `KONTROL-FULL` (everything).

Build them with `uv run kdist --verbose build -jN 'kontrol.*'`; on Linux prefix `CXX=clang++-14` (LLVM 14).
`kdist clean` wipes the build if it gets into a bad state.
`kontrol build` (the user-facing command) selects which of these definitions to use based on `--keccak-lemmas`/`--auxiliary-lemmas`.

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

## The `kontrol` commands

Every subcommand is registered in `cli.py` and implemented as `exec_<name>` in `__main__.py` (dispatching to a `foundry_*` function).
The full set:

- **Setup / build:** `init` (scaffold a Kontrol-ready Foundry project), `setup-storage` (generate symbolic-storage constants), `build` (run `forge build`, generate `foundry.k`, kompile), `load-state` (turn a `vm.dumpState`/`stopAndReturnStateDiff` JSON into a state-diff summary), `version`, `clean`.
- **Prove / inspect:** `prove --match-test <regex>` (the core command), `show <test>` (text KCFG, also `--to-kevm-claims`/`--to-kevm-rules`), `view-kcfg <test>` (interactive TUI), `list` (proofs on disk), `get-model` (counterexample for a node).
- **KCFG surgery (interactive debugging):** `simplify-node`, `step-node`, `section-edge` (split a long edge into pieces — the lever for isolating one slow/failing step), `split-node`, `merge-nodes`, `remove-node`, `minimize-proof`, `refute-node`/`unrefute-node`.

Canonical proof loop, run from a Foundry project root:

```bash
kontrol build                                              # forge build + generate + kompile
kontrol prove --match-test 'MyContract.test.*' -j4         # symbolic execution into a KCFG
kontrol show 'MyContract.test_thing()' --omit-unstable-output   # text view (stable for diffs)
kontrol view-kcfg 'MyContract.test_thing()'                # interactive exploration
```

Key `prove` flags: `--match-test` (repeatable selector), `--reinit` (discard the saved KCFG and restart — **default is resume**), `--max-iterations` (KCFG extensions per run), `--max-depth` (execution steps per `execute` request), `-j`/`--workers` (parallel proofs).
Build the frontier incrementally by rerunning without `--reinit`; cap a single step with `--max-iterations 1 --max-depth 1` to log it (see the Haskell-logging section).

Proof state lives under `out/` in the project root: `out/kompiled/` (the K definition), `out/digest` (rebuild-detection hash of K files + options + Kontrol version), and `out/proofs/<test-id>/` (the pyk `APRProof`/KCFG, read and written by all the inspection commands).
`kontrol clean --proofs` clears them; `--reinit` rebuilds a single proof.

The integration suite's Foundry project at `src/tests/integration/test-data/foundry/` is the handiest sandbox for manual runs — it already has contracts and tests wired up.

## Test suites

Three suites under `src/tests/`, each its own Makefile target (all run via `uv run pytest`, all forward `$(TEST_ARGS)`):

- `make test-unit` → `src/tests/unit` — fast, no compilation or RPC; runs serially.
- `make test-integration` → `src/tests/integration` — compiles + proves real contracts against a Kore RPC server; runs `--numprocesses=4 --dist=worksteal`.
- `make profile` → `src/tests/profiling` — emits `.prof` files (paths printed at the end of the run).
- `make test`/`test-all` runs unit+integration together; `make cov-*` wraps any of them with coverage (`--cov=kontrol --cov-branch`, HTML report in `cov-*-html/`).

Custom pytest options (defined in `src/tests/conftest.py`):

- `--foundry-root PATH` — reuse a pre-kompiled project instead of building one (big speedup when iterating on a single test).
- `--update-expected-output` — **regenerate golden files** rather than asserting against them; this is how you refresh `show` expected output after an intentional change.
- `--force-sequential` — single-threaded proof loop (CI uses this for every integration split).

Golden/expected outputs live under `src/tests/integration/test-data/` (e.g. `show/<Test>.<sig>.expected`); the test lists (`foundry-prove-all`, `foundry-fail`, …) name the contract tests each suite proves.

Running one test:

```bash
uv run pytest src/tests/unit/test_foundry_list.py -v                       # one unit test
uv run pytest src/tests/integration/test_foundry_prove.py -v \
    -k 'AssertTest.test_assert_true' --foundry-root <prekompiled>          # one proof test
```

CI (`.github/workflows/test-pr.yml`) partitions integration tests into four self-hosted jobs by `-k` filter to balance load — **Integration** (everything except the named groups), **CSE** (`test_kontrol_cse or test_foundry_minimize_proof`), **End-to-End** (`test_kontrol_end_to_end or test_kontrol_setup_storage or test_kontrol_counterexample_generation`), and **Profiling** — so adding a test to one of those named groups changes which job runs it.
`.github/workflows/lint-workflows.yml` runs `actionlint` and `zizmor` over `.github/` on every PR; run both locally before touching a workflow.
`.github/actionlint.yaml` declares the self-hosted runner labels (`normal`, `fast`, `MacM1`) that actionlint cannot discover on its own.

### Two fixture worlds (do not mix)

The integration suites split across two Foundry-project fixtures; a test must stay in the world its fixtures belong to:

| Suite (`-k` filter)                   | Test file               | Fixtures / Foundry project       | CI lists                                                                     |
| ------------------------------------- | ----------------------- | -------------------------------- | ---------------------------------------------------------------------------- |
| `test_foundry_prove`                  | `test_foundry_prove.py` | `test-data/foundry/`             | `foundry-prove-all`, `foundry-prove-skip`, `foundry-fail`, `foundry-bmc-all` |
| `test_foundry_minimize_proof`         | `test_foundry_prove.py` | `test-data/foundry/`             | `foundry-minimize`                                                           |
| `test_kontrol_cse` (file-level match) | `test_kontrol_cse.py`   | `test-data/foundry/`             | `foundry-dependency-all`                                                     |
| `test_kontrol_end_to_end`             | `test_kontrol.py`       | fresh project via `kontrol init` | `end-to-end-prove-all`, `end-to-end-prove-skip`                              |

`test_kontrol_end_to_end` builds a real project from scratch — it runs `kontrol init`, copies `test-data/src/` and `test-data/test/` in, then `kontrol build`s it, and proves against that compiled project.
**New cheatcode tests** therefore go in `test-data/test/` and are registered in `end-to-end-prove-all` — they run under `test_kontrol_end_to_end`, not `test_foundry_prove`.

## Dependencies, versioning, and packaging

`deps/` pins exact upstream versions, each file consumed by the build/CI:

- `deps/k_release` (K framework), `deps/kevm_release` (KEVM/evm-semantics), `deps/z3`, `deps/uv_release` — version strings read by the Dockerfiles, CI workflows, and Nix inputs.
- `deps/kevm_release` must match the `kevm-pyk@…@vX.Y.Z` git ref in `pyproject.toml`; keeping `deps/*`, `pyproject.toml`, `flake.nix`, and `uv.lock` in sync (`uv lock --upgrade` + `nix flake update`) is currently a manual step — the `_update-deps/*` automation was removed along with the rest of the secret-using CD.

The Kontrol version is `package/version` (plain text), mirrored in `src/kontrol/__init__.py` (`VERSION`) and `pyproject.toml`; `package/version.sh bump`/`sub` increments and propagates it.
There is no release automation in this repo at the moment: version bumping, the GitHub release, the Cachix pushes, and the Docker Hub image are all done outside CI until the release workflow is reinstated.

Nix: `flake.nix` exports `.#kontrol` (default) built through a uv2nix layering (`nix/kontrol-pyk-pyproject` → `nix/kontrol-pyk` → `nix/kontrol`).
solc-pinned variants are exposed as passthru attributes — `.#kontrol.solc_0_8_13`, `.#kontrol.solc_0_8_15`, `.#kontrol.solc_0_8_22` (defined in `nix/kontrol/default.nix`); CI's Nix job builds `solc_0_8_13`.
`package/test-package.sh` is the post-build smoke test (`kontrol build` + a trivial `kontrol prove` in `package/test-project`).

Two Dockerfiles: `Dockerfile` (release runtime image, pulls `runtimeverification/kframework-k` + `runtimeverificationinc/z3`) and `.github/workflows/Dockerfile` (CI image; its first stage is `FROM ghcr.io/foundry-rs/foundry`, which is why the `with-docker` composite action logs into ghcr.io first).

### Pinning and overriding K toolchain versions with `kup`

`kup` installs the prebuilt K toolchain (`k`, `kevm`, …) and is how you reproduce or override a CI/build version locally.

- Install a specific version — a release tag, a commit hash, or a **local checkout path**:
  ```bash
  kup install kevm --version v1.0.1-f5ffb68        # tag
  kup install kevm --version cede61c               # commit hash
  kup install kevm --version ~/git/evm-semantics   # local working tree
  ```
- Inspect the input dependency tree (the names you can override) with `kup list <package> --inputs`; inputs nest with `/`, e.g. `k-framework/llvm-backend`.
- Override a single dependency with `--override <input-path> <version-or-local-path>` (takes **two** arguments — the input path and the version/path), repeatable for multiple overrides:
  ```bash
  kup install kevm --override k-framework/llvm-backend ~/git/llvm-backend   # local checkout
  kup install kevm --override k-framework/llvm-backend 8aef082              # commit hash
  ```
  This is the way to build, say, `kevm` against an unmerged `llvm-backend` or `haskell-backend` branch without touching `deps/` or `flake.nix`.
- An input shown as `follows <path>` in `--inputs` is linked to that `<path>` — override the `<path>` input instead; `kup` warns (but allows) overriding the followed input directly.

`--version` and `--override` apply equally to `kup install`, `kup shell` (temporary env), and updates.

## Debugging *why* a proof is slow or failing (Haskell-backend logging)

When a proof stalls, fails to close, or a simplification you expect does not fire, the Haskell backend can emit a per-request log explaining *why*: which lemmas Kore applied, which rules Booster tried and rejected (and the reason), and where Booster aborted and fell back to Kore.
This answers the question a timing profile cannot — not "where is the time" but "why is Booster not making progress here".
The fallback to Kore is both the correctness story (Booster could not finish) and the performance story (Kore fallback is the slow path), so the same log explains slow *and* failing steps.

### Turning it on

`kontrol prove` takes three flags (also available on `kontrol simplify-node` and `kontrol step-node`, which share the same RPC options):

- `--haskell-log-dir DIR` — the on switch; captures one `<request-id>.jsonl` bundle per RPC call (each `execute` / `simplify` / `implies`) under `DIR`.
- `--haskell-log-entries E1,E2,...` — which backend entry families to request; defaults to pyk's curated `HASKELL_LOGGING_ENTRIES` (`DebugAttemptEquation,DebugApplyEquation,DebugTerm,Proxy,Detail,Abort,Simplify,Rewrite`) when omitted.
- `--booster-only-simplify` — skip the Kore simplification pass after Booster (so you see exactly what Booster does on its own); definedness `#Ceil` evaluation still goes through Kore.

Each bundle is JSON-lines: one `{"context": [<tag>, ...], "message": <...>}` object per line, one file per RPC request, named for the JSON-RPC request id so concurrent proof workers never collide.
Note the distinction: `--haskell-log-entries` names the *entry selectors* you ask the backend to emit, but the entries that land in the bundle are tagged with lowercase semantic `context` tags (`kore`, `booster`, `abort`, `simplification`, `failure`, …) — so you grep/`jq` the bundles by those tags, not by the selector names.

### Isolating the step to log

Logging a whole proof produces thousands of bundles; the point is to log *one* problematic step.
Build the KCFG up to the frontier of interest, then take a single step with logging on, resuming from the saved proof:

```bash
# advance the KCFG toward the slow/failing frontier, one extension at a time
# (rerun, without --reinit, to resume and step forward)
kontrol prove --match-test 'MyContract.testThing()' --max-iterations 1

# then log just the next step / simplify / implies:
kontrol prove --match-test 'MyContract.testThing()' \
    --max-iterations 1 --max-depth 1 --haskell-log-dir hlog --verbose
```

`--max-depth` bounds execution steps per `execute`; `--max-iterations` bounds KCFG extensions per run.
Use `kontrol view-kcfg` / `kontrol show` to inspect the frontier and pick the node, and `kontrol section-edge` to split a long edge into smaller pieces so you can log a narrower slice.

### Reading the bundles

The bundles are JSON-lines, so `jq` over `hlog/*.jsonl` is the fastest way in. Three recipes cover most debugging:

```bash
# (1) which lemmas Kore actually applied — rule label + source location, by frequency
jq -rc 'select(.message.label?) | "\(.message.label)\t\(.message.location)"' hlog/*.jsonl \
    | sort | uniq -c | sort -rn

# (2) where Booster aborted and fell back to Kore (the message shows what it choked on)
jq -c 'select(.context|index("abort")) | .message' hlog/*.jsonl

# (3) why Booster rejected a rule — the reason strings, by frequency
jq -rc 'select((.context|index("booster")) and (.context|index("failure"))) | .message' hlog/*.jsonl \
    | grep -v '^{' | sort | uniq -c | sort -rn
```

Recipe (3) is usually the payoff; the reason strings map directly to fixes:

| Booster failure reason | What it means | Likely fix |
|---|---|---|
| `Uncertain about definedness of rule due to: non-total symbol Lbl<f>` | Booster won't apply the rule because it can't establish the RHS is defined | Add `[total]` to `<f>`, or `[preserves-definedness]` to the rule |
| `Concreteness constraint violated: term has variables` | A `concrete(...)`-guarded rule met a symbolic argument | Add a `symbolic(...)` variant, or a lemma that handles the symbolic shape |
| `Symbols differ: <term> =/= "N"` / `Values differ: "a" "b"` | The rule's LHS pattern did not match the actual term | The simplification you want needs a differently-shaped lemma, or an earlier rewrite to normalise the term |
| `Condition simplified to #Bottom.` | A `requires` side condition could not be discharged | Provide the missing fact, often via an `[smt-lemma]` |

Kontrol-specific lemmas are supplied to a proof with `--lemmas <file>:<module>` (the module must import `KONTROL-MAIN`); lemmas that belong to the EVM layer live upstream in KEVM (`evm-semantics`).

The two questions this answers:

1. **Why a rule doesn't fire in Booster, especially when it fires in Kore.**
   Cross-reference recipe (1) against recipe (3): a lemma that shows up under "Kore applied" but whose Booster attempt appears in the failure list is the classic "fires in Kore, not in Booster" case, and the failure reason tells you which Booster-friendly form it needs (a definedness attribute, an SMT lemma, a reshaped pattern).
2. **Which steps Booster is failing on.**
   Recipe (2) names the rewrites/simplifications Booster gave up on for this step; those are exactly where a new lemma, a semantics change, or added backend reasoning will move the proof forward.

The logging path is implemented entirely client-side in pyk's `CTermSymbolic`: `--haskell-log-entries` is sent as the per-request `haskell-logging` field, and the entries returned on the response are written to `<haskell-log-dir>/<request-id>.jsonl`.
The flags require pyk's `HASKELL_LOGGING_ENTRIES`/`booster_only_simplify` support (`kframework>=7.1.333`) and the matching `kevm_pyk.utils.legacy_explore` forwarding; they are threaded through `kontrol prove` (direct `CTermSymbolic` construction) and through the `legacy_explore`-based commands (`simplify-node`, `step-node`, `section-edge`, `get-model`, `show --failure-info`).

For authoring and validating new K simplification lemmas against stuck proofs, use the `/writing-kontrol-lemmas` skill.

## Gotchas

- **Any change to `src/kontrol/kdist/` requires a full rebuild** (use the `/build` skill); there is no incremental build within a target.
- **Integration tests require a pre-built kdist.** `make test-integration` without one fails with a missing-artifact error, not a helpful message.
- **`prove.py` uses `multiprocess`, not the stdlib `multiprocessing`.** They have different APIs; don't swap one for the other.
- **`foundry.py` uses `tomlkit` to preserve TOML formatting on round-trip.** This is intentional; don't replace it with a plain TOML parser.
- **`kore-rpc-booster` processes can be left hanging after integration/snapshot-update runs.** Run `pkill -9 -f kore-rpc-booster` afterward, or a stray process interferes with subsequent runs.
