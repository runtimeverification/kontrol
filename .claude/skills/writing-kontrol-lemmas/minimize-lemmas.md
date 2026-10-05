# Minimizing the lemma set

After a lemma chain proves green, the natural-first-cut set is almost
always larger than what's load-bearing. Dead simplification rules widen
the rule search space and slow every future proof, so it's worth the
one-time cost of empirical minimization.

The approach is simple: disable one rule at a time, rerun the spec,
commit the removal if it still passes, restore and move on if it
fails. Order matters — a rule that's removable on its own may become
necessary after an earlier rule is dropped, so put "load-bearing
suspects" first if you want them confirmed against the full set.

## Cost

Each iteration is roughly one kompile+prove cycle (kompile-dominated).
N rules ≈ N × that cycle, unattended. Run once after the chain is
green; delete what the log marks REMOVABLE.

## Tool (in this skill directory)

`minimize-lemmas.py` is the sole driver — stdlib-only Python, all
configuration on the command line. It matches rule blocks of the shape
`    rule [NAME]: … [simplification, …]` at any indent (spaces or tabs,
as long as the rule starts at the beginning of a line) via a single
regex compiled at import time; rename a rule and it stops matching, so
typos in the positional `rules` list are reported as NOT-FOUND rather
than silently ignored.

## Setup

1. Copy `minimize-lemmas.py` into the project (e.g. under `scripts/`),
   or invoke it in place from the skill directory. Stdlib only — no
   virtualenv needed.
2. Optional: freeze a pristine copy of the lemmas file so the script
   can restore from it before the run (useful when iterating on which
   rules to probe). Put the copy anywhere; pass its path to
   `--pristine` below. Example using a `mktemp`-generated path:
   ```bash
   PRISTINE="$(mktemp -t lemmas-original.XXXXXX.k)"
   cp test/kontrol/lemmas.k "$PRISTINE"
   ```
   Without `--pristine`, the lemmas file is taken as-is when the run
   starts.

## Invocation

```bash
./scripts/minimize-lemmas.py \
    --project-root "$(pwd)" \
    --lemmas-file test/kontrol/lemmas.k \
    --spec-runner scripts/kontrol-lemma-test.sh \
    --spec-stem my-spec \
    --expected-passes 4 \
    --pristine "$PRISTINE" \
    rule-a rule-b rule-c
```

Positional arguments are the rule names, in probe order. All config is
on the command line; nothing needs to be edited in the script itself.

Flags:

| Flag | Meaning |
|------|---------|
| `--project-root` | Where to invoke the spec runner from (required). |
| `--lemmas-file` | Path to the K lemmas file, relative to `--project-root` (required). |
| `--spec-runner` | Script used to run the spec. Invoked as `<spec-runner> <spec-stem>` (required). |
| `--spec-stem` | Single argument passed to the spec runner (required). |
| `--expected-passes` | Count of `PROOF PASSED` lines when every claim in the spec passes (required). |
| `rules` | Rule names to probe, positional, in desired order (one or more). |
| `--pristine` | Optional: path to a frozen copy used to reset the lemmas file before the run. |
| `--results-file` | Output TSV path (default: a fresh `$TMPDIR/minimize-lemmas-XXXXXX/results.tsv` created per run — unique suffix via `tempfile.mkdtemp`, so parallel invocations can't collide). |
| `--checkpoint` | Scratch path used to restore after a NECESSARY verdict (default: `$TMPDIR/minimize-lemmas-XXXXXX/checkpoint.k` in the same per-run directory as `--results-file`). |

Run `./minimize-lemmas.py --help` for the full reference.

At startup the script prints `scratch directory: $TMPDIR/minimize-lemmas-XXXXXX`
(unless both `--results-file` and `--checkpoint` are overridden), so
each run gets its own results file and checkpoint. The lemmas file
itself is mutated in place, though, so concurrent invocations are only
safe when each run targets a distinct `--lemmas-file` (e.g. separate
working copies or git worktrees) — there is no locking, and two runs
sharing one lemmas file will interleave edits and corrupt it. Output
is streamed and also written to the results TSV:

```
rule           result
lowbit-or-shl  necessary
chop-simp      removable
```

After the run the lemmas file on disk already reflects the minimal set
(removable rules stay commented out). Permanently delete the commented
blocks — do not leave them behind as `// removed` comments; they
confuse the next reader and git history is authoritative.

## Common redundancies worth probing first

Put these first on the rules list so they get tested against the full
set, where they're most likely to be genuinely removable:

- `modInt pow256` wrappers around bit-extraction patterns — the booster
  often strips them unaided.
- Non-negativity helpers for bitwise ops — built-in simplifications
  cover most cases.
- Non-negativity for `#asWord(...)` / `lengthBytes(...)` — already
  provided upstream; your copy is a duplicate or worse a conflict.
- Duplicated keccak disjointness across `==Int` / `-Int` shapes — keep
  only the shape the prover's arithmetic normaliser actually lands on.

## What minimization does NOT test

- **Soundness.** A minimal set of unsound rules is still unsound. Run
  soundness claims (see `lemma-testing.md`) both before and after
  minimization to make sure nothing regresses.
- **Performance on large proofs.** A rule removable on your lemma-test
  spec might still be load-bearing on a full `kontrol prove` run. If
  the minimized set breaks an end-to-end proof, reinstate the affected
  rule and document it with a comment linking to the failing test.

## Troubleshooting

- **"NOT FOUND — skipping"** — the disable step couldn't locate the
  named rule block. Usually a typo in the positional rules list; check
  the exact name against the lemmas file. The regex matches any
  leading whitespace (spaces or tabs) but requires the rule to start
  at the beginning of a line and carry a `[simplification...]`
  attribute.
- **All rules marked NECESSARY** — almost always means
  `--expected-passes` is wrong, or the spec runner is failing for an
  unrelated reason. Run the spec once manually first and check the
  `PROOF PASSED` count.
- **Ctrl-C during a run** — the script catches `KeyboardInterrupt`,
  restores the lemmas file from the most recent per-iteration
  checkpoint, and re-raises. Results written up to that point are
  preserved in the TSV.
