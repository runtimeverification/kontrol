---
name: writing-kontrol-lemmas
description: >-
  Use when `kontrol prove` leaves pending leaves in the KCFG, times out
  during simplification, or fails to reduce bitwise, keccak, Map, or
  `bool2Word` terms — and the fix needs a new K simplification lemma
  rather than a `kontrol prove` flag.
---

# Writing Kontrol Lemmas

## Overview

A K simplification lemma is a rewrite rule tagged `[simplification]` that
Kontrol/KEVM applies during proof search. When `kontrol prove` gets stuck,
the usual cure is a rule that discharges a side condition or collapses a
composite term (bitwise algebra, keccak disjointness, Map lookups,
`bool2Word` predicates, symbolic `+Bytes` blobs, etc.).

**Core principle:** Never commit a lemma whose reduction you haven't
verified on the actual stuck term. Pair every candidate rule with a unit
test under a `runLemma`/`doneLemma` scaffolding that runs against a
minimal stand-alone kompiled definition — not the full Solidity build.

**Why a separate definition.** `kontrol build` takes minutes and is
invalidated by any `.k` change. A lemma-test definition is just
EVM + `lemmas.k` + the scaffolding — orthogonal to
whatever state `out/kompiled` is in, so you can iterate on lemmas while
an in-flight `kontrol prove` runs.

## When to Use

**Symptoms that a new lemma is needed:**

- `kontrol prove` finishes with "pending" leaves in the KCFG
- A proof times out during simplification
- A branch splits where the path condition is already decidable but K
  can't see it
- The stuck term involves `&Int`, `|Int`, `xorInt`, `>>Int`, `<<Int`,
  `keccak`, `Map:lookup` / `_Map_[_]`, `in_keys`, `bool2Word`, `#lookup`,
  `#asWord`, composite `_+Bytes_` blobs, `modInt pow256` wrappers
- A test_* proof fails with `Matching failed` or unreduced predicates in
  `<k>`

## When NOT to Use

**Symptoms where a lemma is NOT the right answer** — see `flag-fixes.md`:

- `EVMC_BAD_JUMP_DESTINATION` inside a constructor with a symbolic
  `immutable` → use `--symbolic-immutables`
- Enum branches not pruned → `--enum-constraints`
- Coarse KCFG around external calls → `--break-on-calls`
- Real constructor behavior matters for storage layout → `--run-constructor`

Skim `kontrol prove --help` once per stuck proof before committing to
algebra. Flags are cheap, sounder, and invisible in the KCFG.

**Also out of scope:**

- Debugging Z3 / SMT encoding details — this skill edits K simplification
  rules, not the solver. (See `lessons-learned.md` for the bitwise-ops-
  as-uninterpreted consequence and how to work around it.)
- Running the production `kontrol prove` end-to-end — this skill produces
  a rule + probe spec; the final re-run is the user's.
- Rewriting `kontrol build` or Solidity artifacts — lemmas operate on the
  K semantics, not the compiled bytecode.

## Scope boundaries

- **In scope:** Diagnosing stuck KCFG leaves as algebra vs. flag/config,
  writing `[simplification]` rules, scaffolding probe specs under a
  separate lemma-tests kompiled definition, checking soundness with the
  asymmetric `+Int` wrap, and minimizing the resulting rule set.
- **Out of scope:** Modifying `kontrol.toml`'s `require =` target beyond
  the project's existing lemmas file, changing `out/kompiled` (the
  production build), and authoring lemmas that require new sorts beyond
  `Int | Bool | Bytes | Map` without extending `run-lemma.k`'s `StepSort`.

## Usage

The user reports a pending or stuck KCFG leaf from `kontrol prove` and
wants a lemma to close it. Work through the gating checklist
("Before writing a lemma"), then the Workflow section.

```text
Example user request: `kontrol prove` on Foo.testFuzz_bar left a pending
leaf at node 42 — the <k> cell shows bool2Word(L ==Int 0) unreduced and
the path condition has 0 <Int L. Please write a lemma to close it.
```

## Inputs and Assumptions

**Requires:**

- Kontrol project with `kontrol.toml`, a lemmas file listed under
  `[build.default] require = …` (often `test/kontrol/lemmas.k`), and a
  working `kontrol` + `kevm` install. The wrapper resolves `kevm` from
  kontrol's nix-store closure, so `nix-store` must be on `PATH`.
- A stuck / pending KCFG leaf identified via `kontrol show
  <Contract>.<method> --no-minimize`, with the offending subterm and
  the path condition known.
- Write access to the project's lemmas file and permission to create a
  lemma-tests directory (e.g. `test/kontrol/lemma-tests/`) and a
  `scripts/` (or `script/`) entry for the wrapper.

**Optional:**

- Pre-existing `test/kontrol/lemma-tests/` and `scripts/` directories —
  the scaffolding and wrapper are dropped in next to whatever the
  project already uses.
- `auxiliary-lemmas = true` under `[build.default]` in `kontrol.toml`
  (pulls in Kontrol's upstream helper lemmas; check before writing a
  duplicate).

## Outputs (task contract)

- **Produces:**
  - New `[simplification]` rules in the project's lemmas file, each
    paired with a firing claim and a soundness claim (asymmetric `+Int`
    wrap — see `lemma-testing.md`) in a `<name>-spec.k` file under the
    lemma-tests directory.
  - A `PROOF PASSED` run from `scripts/kontrol-lemma-test.sh <stem>`
    confirming the rules fire on the stuck shape against a minimal
    EVM + lemmas definition (no Solidity build).
  - Optionally, a minimized rule set after running
    `scripts/minimize-lemmas.py`, with a per-run
    `$TMPDIR/minimize-lemmas-XXXXXX/results.tsv` log classifying each
    rule as `necessary` or `removable`.
- **Hands off to:** Re-running the original `kontrol prove --match-test
  <Contract>.<method>` to confirm the previously-pending leaf closes.

## Before writing a lemma: is this really an algebra problem?

`pending` in a KCFG leaf does not mean "the theory cannot simplify
this". It means "the prover has not driven this leaf to a terminal
state yet". A pending leaf can be any of:

1. **Algebra-stuck** — the term genuinely needs a new simplification.
   This is what the rest of this skill addresses.
2. **Iteration-exhausted** — the prover hit its per-node step budget.
   Bump `max-iterations` in `kontrol.toml` (or pass `--max-iterations`)
   and re-run before writing anything.
3. **Fail-fast-truncated** — `fail-fast` is on by default, so the
   runner stops as soon as any leaf fails. Sibling leaves that were
   pending when the runner exited are pending because they never got
   worked on, not because they're stuck. Check sibling statuses
   before treating any leaf as algebra-stuck; pass `--no-fail-fast`
   (or set `fail-fast = false` in `kontrol.toml`) to drive all
   branches to completion when you need the full picture.
4. **Flag-curable** — see `flag-fixes.md`. A stuck symbolic-immutable
   JUMPDEST looks exactly like an algebra problem from the outside.

Diagnosis order: (a) sibling statuses, (b) `max-iterations`, (c)
flags in `flag-fixes.md`, (d) algebra. Writing a lemma skips that
ladder and wastes one kompile cycle per attempt.

## Workflow

1. **Diagnose.** `kontrol show <Contract>.<method> --no-minimize | less`.
   Note the stuck node id, the path condition at each pending/failing
   leaf, and the unreduced term in the leaf's `<k>` cell.
2. **Gate it.** Work through the "is this really algebra?" checklist
   above — sibling statuses, `max-iterations`, `flag-fixes.md`. Only
   proceed past this point if the pending leaf's term is genuinely
   one the existing theory can't simplify.
3. **Pick the subterm to probe.** The `<k>` cell typically has a
   whole chain (`JUMPI D I ~> #pc[JUMPI] ~> #execute ~> ...`). You
   only need to wrap the *one* subterm the theory is failing to
   reduce, not the whole chain. See "KCFG → `runLemma` recipes"
   below for the common shapes. Reproduce variables with Kontrol's
   `KV<N>_<argName>:<Sort>` naming verbatim so any
   `concrete(...)` / `symbolic(...)` attributes on lemmas line up
   with the actual ground/symbolic split.
4. **Set up scaffolding** (once per project):
   - Locate the project's lemmas file — it's whatever appears under
     `require =` in `kontrol.toml`'s `[build.default]` (often
     `test/kontrol/lemmas.k`, sometimes `lemmas.k` at the repo root).
   - Create a lemma-tests directory (e.g. `test/kontrol/lemma-tests/`
     if not already present).
   - Copy `run-lemma.k` into the lemma-tests directory. Edit its
     `requires "lemmas.k"` line if the project's lemmas file has a
     different basename — the include resolves via the wrapper's
     `-I` path.
   - Copy `kontrol-lemma-test.sh` into a `scripts/` (or `script/`,
     match the project) directory. Edit the four path variables at
     the top: `SPEC_DIR`, `LEMMAS_DIR`, `DEFN_DIR`, `PROOFS_DIR`.
     `LEMMAS_DIR` must be the directory containing the lemmas file
     (not the file itself).
5. **Write a probe spec FIRST — no new lemmas yet.** At
   `<lemma-tests-dir>/<name>-spec.k`:
   ```k
   requires "run-lemma.k"

   module <NAME>-SPEC
       imports VERIFICATION
       claim [probe]:
           <k> runLemma ( <stuck subterm> ) => doneLemma ( <expected RHS> ) ... </k>
           requires <path condition constraints from the pending leaf>
   endmodule
   ```
   `VERIFICATION` re-exports the project's lemmas via `run-lemma.k`'s
   `imports KONTROL-LEMMAS`, so whatever is already in `lemmas.k`
   (plus `auxiliary-lemmas` if enabled in `kontrol.toml`) is in scope.
6. **Run the wrapper on the probe spec — in the background.** Kompile
   alone is ~60 s per invocation, so synchronous foreground runs freeze
   the conversation:
   ```
   Bash(run_in_background: true, command: "scripts/kontrol-lemma-test.sh <spec-stem>")
   BashOutput(<shell id>)               # poll until the shell exits
   ```
   Never invoke the wrapper with `run_in_background: false` — the
   same rule applies to `minimize-lemmas.py`, which internally calls
   the wrapper once per rule and takes N × one kompile cycle.
   Once the shell has exited, read the tail of the output to conclude:
   - `PROOF PASSED` → the existing theory already simplifies this
     shape. The proof's pending leaf is NOT an algebra problem —
     return to the gating checklist (step 2) and look at iteration
     budget, fail-fast, or a flag.
   - `PROOF FAILED` → inspect the stuck KCFG node
     (`out/proofs-lemma-tests/<spec>/kcfg/` or `kontrol view-kcfg`)
     and the `K_CELL: doneLemma(LHS' #Implies RHS)` diff. `LHS'` is
     how far the booster got; the gap between `LHS'` and `RHS` tells
     you what rule is missing.
7. **Add candidate rules** to the project's lemmas file. Every rule
   must satisfy the four requirements below (concise, sound,
   maintainable, readable). Re-run the wrapper; iterate until the
   probe spec passes.
8. **Check soundness** with an asymmetric claim — see `lemma-testing.md`.
   A rule that passes `runLemma(E) => doneLemma(E)` is not a soundness
   test; wrap in `+Int` so an unsound step surfaces as a numeric diff.
9. **Integrate.** Once the spec passes, the rules are already in the
   project's lemmas file and flow into the next `kontrol build`.
10. **Re-run the original proof** to confirm the previously-pending
    leaf closes.
11. **Minimize** with the driver in `minimize-lemmas.md`. Intuition
    overestimates what's load-bearing; dead simplification rules widen
    the search space and slow every future proof.

## KCFG → `runLemma` recipes

Common stuck-term shapes and how to wrap them. Pick the recipe that
matches the leaf's `<k>` cell.

| Stuck `<k>` cell | Wrap in `runLemma(...)` | `requires` |
|---|---|---|
| `JUMPI DEST bool2Word(C)` at pc P (leaf pending after branch split added C to path) | `bool2Word(C)` | `C` (positive-branch leaf) or `notBool C` (other) — expected RHS is `1` or `0` |
| Storage read `#lookup(M, K)` returning a ternary `ite(isInt(M[K]), ...)` | `#lookup(M, KV0_slot)` | any disjointness / key-presence facts on `M` |
| Composite `chop(A +Int B)` in an arithmetic constraint that won't discharge | `chop(A +Int B)` | `0 <=Int A`, `A +Int B <Int pow256`, etc. |
| `X ==Int keccak(A) +Int C` that won't resolve via collision-resistance | the whole `==Int` | constraints on `C` (e.g. `notBool C ==Int 0`) |
| Bitwise `A &Int (B |Int C)` that stays unreduced | the operator expression | non-negativity: `0 <=Int A`, `0 <=Int B`, `0 <=Int C` |

For anything else, copy the exact subterm from the leaf's `<k>` and
the exact constraints from the pending leaf's path condition. Keep
the wrapped subterm as narrow as possible — wrapping too much just
slows kompile and obscures the failure diff.

## Four requirements for every new lemma

Every lemma in the project's `lemmas.k` must satisfy all four. A rule
that fails one is not acceptable even if the specific claim it was
meant to close goes green.

### 1. Concise — operator nesting depth strictly less than 2

Count the operator tree on each side. Depth = operators you descend
through to reach a leaf.

| Depth | Example | Verdict |
|-------|---------|---------|
| 0 | `A +Int 1` | OK |
| 0 | `A *Int B <Int C` | OK (two ops, none nested) |
| 1 | `(X +Int Y) modInt Z` | OK |
| 1 | `lengthBytes(B) <Int pow256` | OK |
| 2 | `((A +Int B) *Int C) xorInt D` | Reject |
| 3+ | `#asWord(X +Bytes #buf(32, Y +Int 1))` | Reject |

If the stuck term is deeper, decompose it into a chain of depth-≤1
rules. See `lessons-learned.md` → "Decompose stuck terms".

### 2. Sound

The rule must hold for every valuation of its free variables, not only
the one the proof got stuck on. Use the asymmetric `+Int` wrap from
`lemma-testing.md` to catch unsound steps. Unsound rules poison every
future proof that reaches them.

### 3. Maintainable

Phrase as a generic algebraic identity, not a pattern glued to one
stuck expression. A rule whose LHS is a verbatim copy of the stuck
shape fires once in the project's lifetime; a single-identity rule
over operator structure fires wherever that sub-pattern appears.

### 4. Readable

- **Name by the identity:** `add1-sound`, `shift-to-mult`,
  `nonneg-andInt`, `lowbit-or-shl`. Reject: `fix-deposit-stuck`,
  `for-btc-tx-proof`, `close-leaf-17`.
- If the body needs a 3-line comment to explain what it does, the
  rule is doing too much — split it.
- **Parenthesize every bitwise operator explicitly.** The K pretty-
  printer drops same-precedence parens (see `lessons-learned.md` →
  "Pretty-printer parens") so the written rule's AST matches what a
  reader parses at a glance.

## Attribute quick reference

| Attribute                 | Effect                                               |
| ------------------------- | ---------------------------------------------------- |
| `[simplification]`        | Used by the prover as a simplification equation.     |
| `[simplification(N)]`     | Priority `N` (lower = applied earlier).              |
| `[preserves-definedness]` | Booster may apply in definedness-required contexts. |
| `[concrete(X,Y,...)]`     | Only fire when listed variables are ground.          |
| `[symbolic(X,Y,...)]`     | Only fire when listed variables are symbolic.        |
| `[smt-lemma]`             | Also hand equation to Z3 as a quantified axiom.      |
| `[comm]`                  | LHS is commutative; match either argument order.     |
| `[priority(N)]`           | Non-simplification priority (ordering vs other rules). |

## K built-in reference — `domains.md`

The standard sorts the scaffolding wraps (`Int`, `Bool`, `Bytes`, `Map`,
`Set`, `List`) and their operators (`+Int`, `-Int`, `modInt`,
`&Int`/`|Int`/`xorInt`/`>>Int`/`<<Int`, `lengthBytes`, `+Bytes`, map
lookup / `in_keys`, ...) are declared in the K framework's
`k-distribution/include/kframework/builtin/domains.md` — from the
upstream `runtimeverification/k` GitHub repository. Consult it to
confirm:

- **Operator precedence / associativity** — declared via `[left]` on
  each syntax rule. Relevant when parenthesizing bitwise terms copied
  out of the KCFG (see `lessons-learned.md` → "Pretty-printer parens").
- **SMT encoding** — `smt-hook(...)` / `smtlib(...)` attributes show
  exactly what Z3 sees. Bitwise ops map to uninterpreted `andInt` /
  `orInt` / `xorInt` SMT symbols (see `lessons-learned.md` → "Z3 sees
  bitwise ops as uninterpreted").
- **Built-in simplifications** — the `INT-SYMBOLIC` and `INT-KORE`
  modules ship rules like `I +Int 0 => I`, `X modInt N => X requires
  0 <=Int X andBool X <Int N`, `X <<Int 0 => X`, plus arithmetic
  normalisation (`concrete(I), symbolic(B)` reorderings). Check here
  before writing a new rule; duplicates are a common source of
  minimization removals (`minimize-lemmas.md`).

EVM-specific things — `keccak`, `bool2Word`, `chop`, `#lookup`,
`#asWord`, `#buf`, `pow256` — are NOT in `domains.md`; they come from
`kevm_pyk/kproj/evm-semantics/*.md` (`lessons-learned.md` → "-I
include paths").

## Interpreting results

| Outcome | Meaning |
|---------|---------|
| `PROOF PASSED: MOD.label` | Theory rewrote `runLemma(LHS)` to `doneLemma(LHS')` matching `doneLemma(RHS)`. |
| `PROOF FAILED: MOD.label` | Rewrite stalled. Output shows stuck node id, `K_CELL: doneLemma(LHS' #Implies RHS)` diff, and accumulated path condition. |

Rerun a single claim with `--claim <NAME>-SPEC.<label>`. Inspect the
KCFG graph with `kontrol view-kcfg` pointed at
`out/proofs-lemma-tests/<spec>/kcfg/`.

## Common gotchas

- **Do NOT put `runLemma` / `doneLemma` syntax in `lemmas.k`.** That
  file is pulled into production `kontrol build` via `kontrol.toml`'s
  `require`. Test scaffolding must live in a separate file
  (`run-lemma.k`) only `requires`'d from spec files.
- **`runLemma(X) => doneLemma(X)` is NOT a soundness test.** It passes
  trivially for unsound rules — both sides reduce identically. Use
  asymmetric wrap (`lemma-testing.md`).
- **`1 +Int 1 => 2` passes regardless of symbolic rules.** K hooks
  evaluate concrete arithmetic before symbolic rules fire. Exercise
  rules with symbolic variables (`Y:Int +Int 1`).
- **Stale cached proof state.** `kevm prove` caches; the wrapper
  always passes `--reinit`. Manual invocations need it explicitly.
- **`KRYPTO differs from previous declaration`** = `kevm` from one
  install vs. `out/...-kompiled` from another. The wrapper resolves
  `kevm` from kontrol's nix-store closure specifically to avoid this.
- **Compile error "Found syntax declaration in proof module"** — your
  spec file defined syntax in the `*-SPEC` module. Keep syntax in
  `VERIFICATION` (`run-lemma.k`); the proof module only holds claims.
- **The K pretty-printer drops same-precedence parens.** An expression
  like `A >>Int B <<Int C xorInt D &Int E` in the KCFG view is not
  the left-to-right read. Parenthesize explicitly when copying into a
  spec. See `lessons-learned.md`.

Full list: `lessons-learned.md`.

## Validation

- [ ] `<lemma-tests-dir>/<name>-spec.k` exists with both a firing claim
      and a soundness claim (asymmetric `+Int` wrap — see
      `lemma-testing.md`). The identity claim `runLemma(E) =>
      doneLemma(E)` alone is NOT a soundness test.
- [ ] `scripts/kontrol-lemma-test.sh <stem>` reports `PROOF PASSED` for
      every claim in the spec module (run in the background and polled
      with `BashOutput` — never synchronous; kompile alone is ~60 s).
- [ ] Each new rule satisfies the "Four requirements" (operator nesting
      depth < 2, sound, generic/algebraic, readable with an identity-
      based name).
- [ ] The original `kontrol prove --match-test <Contract>.<method>` run
      closes the previously-pending leaf.
- [ ] `scripts/minimize-lemmas.py` has been run on the new rule set
      and all rules retained are marked `necessary` in the per-run
      `$TMPDIR/minimize-lemmas-XXXXXX/results.tsv` (or wherever
      `--results-file` pointed).
- [ ] No `runLemma` / `doneLemma` syntax appears in the project's
      production lemmas file — only in `run-lemma.k` and the spec
      files under the lemma-tests directory.

## Supporting files in this skill

| File | Purpose |
|------|---------|
| `run-lemma.k` | The `runLemma`/`doneLemma` scaffolding. Copy into project's lemma-tests dir. |
| `kontrol-lemma-test.sh` | kompile + prove wrapper. Copy into project's `scripts/`; adjust paths at top. |
| `extract-stuck-term.py` | Dumps symbolic terms from KCFG split targets. |
| `flag-fixes.md` | `kontrol prove` flags that cure common symptoms without a lemma. |
| `lemma-testing.md` | Soundness vs firing; asymmetric wrap; claim patterns. |
| `lessons-learned.md` | Pretty-printer parens, Z3 opacity, decomposition strategy. |
| `minimize-lemmas.md` | Minimization workflow — usage + troubleshooting. |
| `minimize-lemmas.py` | Driver: comments out each listed rule in turn, reruns the spec, records REMOVABLE / NECESSARY / NOT-FOUND. All parameters are CLI args; scratch and results paths default to a fresh per-run `$TMPDIR/minimize-lemmas-XXXXXX/`. |
