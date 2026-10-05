# Lessons learned

Read before writing the next spec. These apply to any stuck-term
investigation in Kontrol/KEVM.

## "Proof module" = the module with `claim`s, not every reachable module

`kprove`'s "Found syntax declaration in proof module. Only tokens for
existing sorts are allowed." error applies *only* to the module
containing the claims. Any other module — `VERIFICATION`, your lemma
module, EVM, FOUNDRY — can declare syntax freely as long as it's
reached via `imports`/`requires` and isn't itself the proof module.
`--main-module VERIFICATION` on kompile cements this: VERIFICATION is
compiled as the regular main module, syntax and all.

That's why one shared scaffolding file (`run-lemma.k`) works for every
spec, rather than having to inline `runLemma`/`doneLemma` per spec.

## Decompose stuck terms into small generic rules, not one composite

It is tempting to close a stuck term with one pattern-matched lemma
whose LHS is a verbatim copy of the stuck structure. That rule fires
once, on that exact shape, and is dead weight afterwards. Decomposing
the reduction into a chain of small single-identity rules — each
stripping one operator or distributing one layer — buys reuse: every
rule is a standalone algebraic identity that fires in any future proof
where the same sub-pattern appears. Small rules compose without looping
as long as each strictly reduces the term's structure.

The cost is one-time: more rules to write. The payoff is cumulative:
the second stuck term in the same family closes for free.

### Example family: short-string length extraction

Solidity packs a short string (L ≤ 31) into a storage slot as:

```
slot = (L <<Int 1) |Int (((maxUInt256 >>Int (L <<Int 3)) xorInt maxUInt256) &Int W)
```

The decoder extracts L as `(slot /Int 2) &Int 0x7F`. Rather than one
composite rule matching the full nested shape, the reduction splits
into:

```
div2-to-shr               X /Int 2            => X >>Int 1
shr-over-or               (A |Int B) >>Int N  => (A >>Int N) |Int (B >>Int N)
shr-over-and              (A &Int B) >>Int N  => (A >>Int N) &Int (B >>Int N)
shr-over-xor              (A xorInt B) >>Int N => (A >>Int N) xorInt (B >>Int N)
shl-shr-cancel            (X <<Int N) >>Int N => X
and-over-or               C &Int (A |Int B)   => (C &Int A) |Int (C &Int B)
and-over-xor              C &Int (A xorInt B) => (C &Int A) xorInt (C &Int B)
and-assoc-left            C &Int (A &Int B)   => (C &Int A) &Int B
maxSInt8-and-identity     maxSInt8 &Int L     => L    (0 <= L <= maxSInt8)
maxSInt8-and-shr-maxUInt256
                          maxSInt8 &Int (maxUInt256 >>Int N) => maxSInt8   (N < 250)
(built-in)                X xorInt X          => 0
(built-in)                0 &Int X            => 0
(built-in)                X |Int 0            => X
```

Each rule is one algebraic identity with depth ≤ 1 (with one depth-2
exception for a double-shift closing rule). Each is independently
verified via `runLemma`/`doneLemma`. Once in place, they fire on any
future proof that reads back a short string from storage.

The `(built-in)` entries above and a handful of arithmetic
normalisations (`I +Int 0 => I`, `X modInt N => X` when `0 <=Int X <Int
N`, `X <<Int 0 => X`) are shipped by K itself in the `INT-SYMBOLIC` /
`INT-KORE` modules of `k-distribution/include/kframework/builtin/
domains.md`. Skim that file before adding non-negativity / identity
helpers for `Int`, `Bytes`, or `Map` — it's where the duplicates in
`minimize-lemmas.md`'s "Common redundancies" list come from.

## Z3 sees bitwise ops as uninterpreted

K's SMT encoding hooks the bitwise integer operators (`&Int`, `|Int`,
`xorInt`, `<<Int`, `>>Int`) as uninterpreted functions. The `smtlib(...)`
attributes on the syntax declarations in
`k-distribution/include/kframework/builtin/domains.md` (e.g.
`smtlib(andInt)`, `smtlib(xorInt)`) show this directly — grep for the
operator and the SMT symbol falls out. Two practical consequences:

### Non-negativity doesn't propagate at the Z3 level

But the booster fills in most of the gap through built-in
simplifications. In practice you only have to state explicit
`0 <=Int (op A B) => true requires 0 <=Int A andBool 0 <=Int B` rules
for the specific operator(s) the booster can't discharge on the stuck
term at hand. Add them greedily when a chain gets stuck, then prune
the redundant ones (see `minimize-lemmas.md`).

### `X <<Int N <Int Y` is opaque

Even with a linear bound like `X <=Int 31` in scope, Z3 won't verify
`(X <<Int 3) <Int 256`. Rewrite the shift to multiplication with a
`concrete(N, Y)`-gated simplification:

```k
rule [shl-lt-concrete]:
    ( X <<Int N ) <Int Y => true
    requires 0 <=Int X
             andBool X *Int ( 2 ^Int N ) <Int Y
             andBool 0 <=Int N
    [simplification, preserves-definedness, concrete(N, Y)]
```

Linear arith takes it from there. The `concrete(N, Y)` guard keeps the
rule from firing on symbolic shifts where it wouldn't help anyway.

## Catch unsoundness with an asymmetric `+Int` wrap

Covered in detail in `lemma-testing.md`. Short version: `runLemma(E)
=> doneLemma(E)` passes even for unsound rules. Wrap in a linear
combination so an unsound step surfaces as a numeric diff.

## The K pretty-printer drops same-precedence parens

Same-precedence bitwise operators don't get parenthesized in the
pretty-printed KCFG view, so an expression like

```
A >>Int B <<Int C xorInt D &Int E
```

is **not** the left-to-right read. K's precedence tables group e.g. the
shift arguments before the xor, and `&Int` before `|Int`. The rendering
and the internal AST diverge.

When copying a stuck term into `runLemma(...)`, explicitly parenthesize
every bitwise operator so the spec's parse matches the internal AST. If
a claim fails matching on a term that *looks* identical to the log,
suspect this first — evaluate both candidate parses at a concrete
instantiation and compare to the value the source-level code computes
to disambiguate. The precedence and associativity that drive this are
declared on each operator's `syntax` rule in `k-distribution/include/
kframework/builtin/domains.md` (`[left]` annotations on `_&Int_`,
`_|Int_`, `_xorInt_`, `_<<Int_`, `_>>Int_` etc.).

## Minimize your lemma set — intuition overestimates what's needed

When closing a stuck term, the natural move is to add every helper that
*could* be relevant: one non-negativity rule per bitwise op, `modInt`
strippers, identity rules, etc. The initial set is usually a couple of
times larger than what's actually load-bearing. Common redundancies:

- `modInt pow256` wrappers around bit-extraction patterns — the booster
  often strips them on its own.
- Non-negativity helpers for bitwise ops — most cases fall to built-in
  simplifications; usually only one or two operator families genuinely
  need an explicit rule. The K-shipped simplifications for `Int` live in
  `INT-SYMBOLIC` / `INT-KORE` inside `k-distribution/include/kframework/
  builtin/domains.md`; skim it to see what's already covered.
- Non-negativity for common KEVM predicates like `#asWord(...)` or
  `lengthBytes(...)` — already provided upstream; your copy is a
  duplicate at best, a conflict at worst.

After the chain proves green, minimize empirically. See
`minimize-lemmas.md` for the driver.

Order matters during minimization — different orders can yield
different minimal sets, but any minimal set is strictly better than the
initial pile.

## Keep `==Int`-vs-`==K` consistent at Map key sort

Kontrol's Map propagation lemmas (`M [K <- V] [K']`, `K in_keys(...)`)
typically want their key comparisons in one arithmetic sort. If your
keys are `Int` (keccak-derived slot offsets are), phrase the
simplifications over `K ==Int K'` rather than `K ==K K'`. Mixing
introduces an extra reduction step (`X:Int ==K Y:Int => X ==Int Y`)
that the booster may or may not take. The underlying `Map` primitives
(`_Map_`, `_|->_`, `Map:lookup`, `Map:update`, `in_keys`) are declared
in the "Map" section of K's `domains.md`; check there for their hooks
and any built-in simplifications before adding your own.

## Targeted predicate rewrites beat generic ones

A tempting rule shape is:

```k
rule [too-broad-eq-zero]:
    L:Int ==Int 0 => false  requires 0 <Int L
    [simplification, preserves-definedness]
```

This fires on every `X ==Int 0` the booster encounters and forces an
SMT check on `0 <Int X`, slowing the whole proof to a crawl on symbolic
paths. Prefer the minimal shape that actually closes the stuck term,
e.g.

```k
rule [bool2Word-notBool-eq-zero]:
    bool2Word ( notBool ( L:Int ==Int 0 ) ) => 1
    requires 0 <Int L
    [simplification, preserves-definedness]
```

Targeted rewrites keep the search space small and fire exactly where
they're needed.

## Ignore `$PATH` — derive `kevm` from kontrol's closure

The `kevm` binary must match the `kontrol` version. Kompile tags the
output definition with `kevm`'s build hash, and `kevm prove` refuses to
load a definition whose hash doesn't match its own runtime. A drive-by
`kevm` on `$PATH` — from a sibling checkout, an older nix-profile, a
pip install — mismatches silently or fails with
`KRYPTO differs from previous declaration`. When it doesn't fail, rule
renames across versions can cause the same claim to simplify
differently without any error.

The wrapper script therefore **ignores `$PATH` entirely** and picks
`kevm` out of `kontrol`'s own nix-store closure. A plain `kevm-*` glob
would also match `kevm-pyk` / `kevm-pyk-env` (pure-Python packages with
no `bin/kevm`), so the filter requires a working `bin/kevm` to exist.

## `kevm` vs `kevm-pyk` — always use `kevm`

- **`kevm-pyk`** is the pure-Python package. Ships no wrapper binary,
  exports none of the env vars the kompile/prove steps need. Never
  invoke directly.
- **`kevm`** is the nix-wrapped binary. Its `bin/kevm` sets `KDIST_DIR`
  (the prebuilt `evm-semantics.plugin` / `krypto.a` kdist target) and
  `NIX_LIBS` (`-L` flags for openssl / secp256k1) before exec'ing the
  underlying Python entry point. Only the wrapped binary lets
  `kevm kompile-spec --with-llvm-library` link the booster against the
  prebuilt plugin. Calling `kevm-pyk` directly fails with
  `Target undefined or not built: evm-semantics.plugin`.

## `-I` include paths, explained

`kontrol-pyk-env` contains the `.md` source files the spec transitively
requires at kompile time, under `lib/pythonX.Y/site-packages/`:

| Path | Holds |
|------|-------|
| `kontrol/kdist`                | `foundry.md`, `cheatcodes.md`, `kontrol_lemmas.md`, `keccak.md`, ... |
| `kevm_pyk/kproj/evm-semantics` | `evm.md`, `evm-types.md`, `schedule.md`, `word.md`, ... |
| `kevm_pyk/kproj/plugin`        | `plugin/krypto.md` |

These are the **source** `.md` files consumed by the K front end at
kompile time. They're distinct from the compiled kdist artifacts that
`KDIST_DIR` points the wrapped `kevm` at during link — those live under
the `kevm` package's `evm-semantics/` subtree and are consumed by
`llvm-kompile`, not by the K front end.

K's own standard library — `domains.md` (`Int`/`Bool`/`Bytes`/`Map`
sorts and their operators) plus `kast.md` et al. — is NOT under any of
the three paths above. It ships with the `k` binary itself under
`k-distribution/include/kframework/builtin/` and is resolved
automatically by `k`'s built-in include path; no `-I` flag in
`kontrol-lemma-test.sh` points at it. To inspect it locally, look up
`k`'s own nix-store path (the wrapped `kevm` pulls it in as a runtime
dep) or browse the upstream GitHub repo `runtimeverification/k` at
`k-distribution/include/kframework/builtin/domains.md`.
