---
description: Build the Kontrol kdist. Use when kdist needs to be compiled or after any change to K semantic files in src/kontrol/kdist/.
---

Build the Kontrol project by running the build script and capturing output to a tmp file.

> **Note:** The build can take several minutes (longer if K needs to be installed first).
> Always run it as a standalone step — never chain it with test commands or other long-running operations in the same tool call, to avoid hitting the 10-minute tool timeout.

```bash
./scripts/build-kontrol > /tmp/kontrol-build.log 2>&1
```

The script handles everything: navigating to the repo root, checking/installing the correct K version, `uv sync`, `kdist clean`, and the full build.

If the script exits successfully, do not inspect `/tmp/kontrol-build.log`.

## On failure

Search `/tmp/kontrol-build.log` for K compiler errors:

```bash
rg -n "\[Error\]" /tmp/kontrol-build.log
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
