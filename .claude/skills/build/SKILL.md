---
name: build
description: Full Kontrol build. Use whenever a build is needed. Handles K version check/install, uv sync, kdist clean, and kdist build.
---

Build the Kontrol project by running the build script and capturing output to a log file.

> **Note:** The build takes well over ten minutes from a clean `kdist` (longer if K needs to be installed first), so a foreground call would hit the tool timeout and be killed mid-build.
> Always start it in the background and poll, and never chain it with test commands or other long-running operations in the same tool call.

Start the build:

```bash
./scripts/build-kontrol > "/tmp/kontrol-build-${CLAUDE_SESSION_ID}.log" 2>&1
```

Run that with `run_in_background: true`, then poll the shell with `BashOutput` until it exits.
The per-session log name keeps concurrent builds (multiple worktrees or sessions) from overwriting each other's output.

The script handles everything: navigating to the repo root, checking/installing the correct K version, `uv sync`, `kdist clean`, and the full build.

If the script exits successfully, do not inspect the log.

## On failure

Search the log for K compiler errors:

```bash
rg -n "\[Error\]" "/tmp/kontrol-build-${CLAUDE_SESSION_ID}.log"
```

K compiler errors have this structure:

```
[Error] Inner Parser: Parse error: unexpected token 'X' following token 'Y'.
    Source(src/kontrol/kdist/cheatcodes.md)
    Location(line,col,line,col)
    42 |    <offending line>
           ^~~~
```

Read the lines around the reported `Location` in the source file to understand the context, then report the Source + Location + offending line to the user and wait for instructions.

Do not retry automatically.
