---
description: Add a new Foundry cheatcode to Kontrol (K rules, selector, Solidity test, CI registration). Use when implementing a new vm.* or Kontrol-proprietary cheatcode.
argument-hint: <cheatcode_signature>
---

Add a new Foundry cheatcode to Kontrol. The cheatcode to implement is: $ARGUMENTS

Follow these steps:

1. **Add the cheatcode section** in `src/kontrol/kdist/cheatcodes.md`, in the appropriate location among the other cheatcode rules.
   Follow the documentation style of adjacent sections (header, Solidity signature block, prose explanation, K rule).

   K rule template:
   ```k
       rule [cheatcode.call.<name>]:
            <k> #cheatcode_call SELECTOR ARGS => .K ... </k>
            <output> _ => #bufStrict(32, /* result */) </output>
         requires SELECTOR ==Int selector ( "<cheatcode_signature>" )
         [preserves-definedness]
   ```

   ABI-encoded ARGS: each parameter occupies 32 bytes — `#asWord(#range(ARGS, N*32, 32))` for the Nth argument (0-indexed).
   If the cheatcode writes state instead of returning a value, omit `<output>` and write to the appropriate configuration cell.

2. **Add the selector rule** in the implemented selectors list:
   ```k
   rule ( selector ( "<cheatcode_signature>" ) => <computed_selector_int> )
   ```
   Compute the decimal selector with `./scripts/selector "<cheatcode_signature>"`.
   If the cheatcode was previously in the non-implemented list, move it instead of duplicating it.

3. **Extend the subconfiguration** (at the top of `cheatcodes.md`) if the implementation requires storing new state across calls.
   Document any new cell with a comment explaining its purpose.

4. **Add Solidity tests** in `src/tests/integration/test-data/test/`.
   Check first whether a test already exists.
   Naming: `<CheatcodeName>.t.sol`, contract `<CheatcodeName>Test`.

   Choose the test strategy based on what the cheatcode affects:
   - **Assertion-testable** (effect visible at Solidity level): use `assert*` calls directly.
     Example: `computeCreateAddress` — predict a value and assert it matches.
   - **KCFG-testable** (effect is on proof structure, not a runtime value): use a golden expected-output file in `test-data/show/`.
     Examples: `forgetBranch` (removes a branch), symbolic variable renaming (changes KCFG node labels), `console.log` (emits output not visible to assertions).
     Add the test to `end-to-end-prove-show` so the snapshot is captured and compared on each run.

5. **Register tests** in `src/tests/integration/test-data/`:
   - Add passing signatures to `end-to-end-prove-all`
   - Add expected-failure signatures to `foundry-fail` (if any)
   - Remove from `end-to-end-prove-skip` if present

6. **Rebuild** using the `/build` skill, then run the new tests under the end-to-end suite:
   ```bash
   make test-integration TEST_ARGS="-k 'test_kontrol_end_to_end and <TestClass>'"
   ```

After all steps, summarise what was added and which files were changed.
