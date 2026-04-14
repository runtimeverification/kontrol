---
description: Update expected output golden files for integration test suites. Use after changes to K semantics or proof strategies that legitimately alter KCFG output.
---

Update expected output snapshots for integration test suites.

> **Note:** This process can be very lengthy. Running all suites can take 30+ minutes, with the CSE + minimize suite being the slowest.
> Prefer targeting a specific suite (`--foundry`, `--cse`, or `--end-to-end`) or a single test (`-k <filter>`) unless a full update is explicitly needed.
> Always run as a background task to avoid timeouts.

```bash
./scripts/update-expected-output [--foundry] [--cse] [--end-to-end] [-k <filter>]
```

No suite flag runs all three suites in order.

```bash
# Single suite
./scripts/update-expected-output --end-to-end

# Single test within a suite
./scripts/update-expected-output --end-to-end -k ComputeCreateAddressTest

# All suites
./scripts/update-expected-output
```

After the script finishes, run `git status` to identify which snapshot files were modified, then summarise the changes.
