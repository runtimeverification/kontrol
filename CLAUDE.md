# Kontrol — Project Conventions

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
