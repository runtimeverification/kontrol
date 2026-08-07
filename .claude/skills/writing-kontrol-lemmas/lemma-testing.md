# Testing lemmas: soundness vs firing

The `runLemma`/`doneLemma` workflow naturally tests "does the rule
fire / does the theory simplify X to Y". It does NOT cleanly test
soundness. Getting this wrong means an unsound rule can silently pass
the spec and then poison every future proof it reaches.

## Claim patterns that are NOT soundness tests

### Identity claim

```k
claim [firing]:
    <k> runLemma(E) => doneLemma(E) ... </k>
```

Trivially passes for *any* rule, sound or unsound — both sides reduce
identically under whatever theory is in scope.

### Concrete numeric claim

```k
claim [firing]:
    <k> runLemma(5 +Int 1) => doneLemma(6) ... </k>
```

K evaluates concrete `+Int` via a built-in hook before the symbolic
rule gets a chance. This doesn't catch an unsound
`X:Int +Int 1 => 8888888 [simplification]` either.

## The cheap soundness test: asymmetric linear wrap

Wrap the stuck expression in something linear (`+Int`, `-Int`) where LHS
and RHS are *mathematically* equal but *syntactically* different enough
that an unsound reduction surfaces as a numeric discrepancy:

```k
claim [add1-sound]:
    <k> runLemma ( (X:Int +Int 1) -Int X ) => doneLemma ( 1 ) ... </k>
```

If `X +Int 1 => 8888888` fires, LHS becomes `8888888 -Int X`, RHS stays
`1`, and the claim fails with a counterexample on `X`. One claim, clear
failure mode, cheap to write.

## Pattern for new rules: firing + soundness, side by side

Every new simplification rule should ship with two claims in its spec:

```k
// Checks the rule actually fires on the stuck shape.
claim [<name>-firing]:
    <k> runLemma ( <stuck LHS copied verbatim from KCFG> )
     => doneLemma ( <expected RHS> )
    ... </k>

// Wraps LHS in a linear context. An unsound step exposes itself
// as a numeric mismatch between the two sides.
claim [<name>-sound]:
    <k> runLemma ( ( <stuck LHS> ) +Int 42 )
     => doneLemma ( <expected RHS> +Int 42 )
    ... </k>
```

The `+Int 42` (or whatever constant) has to be chosen so that concrete
evaluation of RHS doesn't short-circuit before the rule gets a chance
to fire on LHS. When in doubt, use a symbolic `Z:Int` instead of `42`.

## Catching unsoundness from dropped side conditions

A common unsound rewrite is dropping a `modInt pow256` or flipping the
sign of a shift. The wrap catches these:

```k
// Suppose a candidate rule incorrectly rewrites
//   chop(A +Int C)  =>  A +Int C       (should be  A +Int chop(C))
// This passes an identity claim. Under the wrap:
claim [chop-unsoundness-probe]:
    <k> runLemma ( ( chop(A:Int +Int pow256) ) +Int 1 )
     => doneLemma ( 1 )
    ... </k>
// Fails: the unsound rule reduces LHS to pow256 +Int 1, not 1.
```

## Using `concrete(...)` / `symbolic(...)` attributes

K hooks evaluate concrete arithmetic eagerly. If you want to test a rule
that only fires on *symbolic* arguments, either:

- Declare it `[symbolic(X)]` so the rule is gated on X being non-ground.
- Test against a `X:Int` variable rather than a concrete literal — the
  rule will fire if it's supposed to.

And conversely, rules meant to fire only when an argument is concrete
(`shl-lt-concrete`, storage-disjointness on a concrete offset) need
`[concrete(N,Y)]` or the prover may decline to apply them even where
the proof would benefit.

## Debugging a `PROOF FAILED`

A `kevm prove` failure emits:

- **`Node id:`** the stuck KCFG node.
- **`Failure reason: Matching failed.`** + a `K_CELL:
  doneLemma(LHS' #Implies RHS)` diff — LHS' is what the theory reduced
  LHS to; RHS is what the claim expects.
- **`Path condition:`** accumulated constraints at the stuck node.

Workflow:

1. Compare LHS' and RHS. What operator did LHS' fail to rewrite? That's
   the missing lemma.
2. Check the path condition — are the side conditions your rule requires
   actually in scope? A missing `0 <=Int X` or `N <Int 256` is a common
   cause.
3. Inspect with `kontrol view-kcfg` pointed at the proof's `kcfg/`
   directory for the graph view.
4. Re-run one claim with `--claim <NAME>-SPEC.<label>` to iterate fast.
