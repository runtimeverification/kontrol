// ── runLemma/doneLemma scaffolding ─────────────────────────────────────────
// Lets us exercise candidate simplification rules with kevm prove,
// without spinning up a full Solidity proof.
//
// Usage in a spec file:
//
//     requires "run-lemma.k"
//
//     module FOO-SPEC
//         imports VERIFICATION
//         claim [foo]:
//             <k> runLemma ( LHS ) => doneLemma ( RHS ) ... </k>
//     endmodule
//
// Kompile the spec with `--main-module VERIFICATION --syntax-module
// VERIFICATION` (see kontrol-lemma-test.sh). This keeps the scaffolding's
// syntax declarations in a regular module — the spec module only holds
// claims, so kprove's "no syntax in proof module" check is satisfied.
//
// IMPORTANT: NOT to be pulled into the production `kontrol build`. The
// production lemmas file (typically `test/kontrol/lemmas.k`) is listed
// under `require =` in `kontrol.toml`; this scaffolding file is NOT.
// Spec files `requires` it directly, and spec files are only compiled
// under a separate `out/lemma-tests-kompiled` definition.
//
// Do NOT move runLemma/doneLemma declarations into the production
// lemmas.k itself — doing so pulls the test scaffolding into every
// real proof. See SKILL.md §"Common gotchas".
//
// Extend StepSort with additional sorts (Set, custom sorts, ...) if
// runLemma(<term>) needs to wrap something beyond Int/Bool/Bytes/Map.

// Adjust this path to the project's lemmas file if it is not "lemmas.k"
// sitting beside this scaffolding file. Kompile's `-I` flags (set by the
// wrapper script) determine where the requires resolves from.
requires "lemmas.k"

module VERIFICATION
    imports KONTROL-LEMMAS

    syntax StepSort ::= Int | Bool | Bytes | Map
    syntax KItem ::= runLemma ( StepSort ) [symbol(runLemma)]
                   | doneLemma( StepSort )
    rule <k> runLemma(T) => doneLemma(T) ... </k>

endmodule
