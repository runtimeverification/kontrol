Keccak Assumptions
==============

The provided K Lemmas define assumptions and properties related to the keccak hash function used in the verification of smart contracts within the symbolic execution context.

```k
module KECCAK-LEMMAS
    imports FOUNDRY
    imports INT-SYMBOLIC
```

1. The result of the `keccak` function is always a non-negative integer, and it is always less than 2^256.

```k
    rule 0 <=Int keccak( _ )             => true [simplification, smt-lemma]
    rule         keccak( _ ) <Int pow256 => true [simplification, smt-lemma]
```

2. The result of the `keccak` function applied on a symbolic input does not equal any concrete value.

```k
    // keccak does not equal a concrete value
    rule [keccak-eq-conc-false]: keccak(_A)  ==Int _B => false [symbolic(_A), concrete(_B), simplification(30), comm]
    rule [keccak-neq-conc-true]: keccak(_A) =/=Int _B => true  [symbolic(_A), concrete(_B), simplification(30), comm]
```

In addition, equality involving keccak of a symbolic variable is reduced to a comparison that always results in `false` for concrete values.

```k
    rule [keccak-eq-conc-false-ml-lr]: { keccak(A) #Equals B } => { true #Equals keccak(A) ==Int B } [symbolic(A), concrete(B), simplification]
    rule [keccak-eq-conc-false-ml-rl]: { B #Equals keccak(A) } => { true #Equals keccak(A) ==Int B } [symbolic(A), concrete(B), simplification]
```

3. Injectivity of Keccak. If `keccak(A)` equals `keccak(B)`, then `A` must equal `B`.

In reality, cryptographic hash functions like `keccak` are not injective. They are designed to be collision-resistant, meaning it is computationally infeasible to find two different inputs that produce the same hash output, but not impossible.
The assumption of injectivity simplifies reasoning about the keccak function in formal verification, but it is not fundamentally true. It is used to aid in the verification process.

```k
    // keccak is injective
    rule [keccak-inj]: keccak(A) ==Int keccak(B) => A ==K B [simplification]
    rule [keccak-inj-ml]: { keccak(A) #Equals keccak(B) } => { true #Equals A ==K B } [simplification]
```

4. Negating keccak. Instead of allowing a negative value, the rule adjusts it within the valid range, ensuring the value remains non-negative.

```k
    // chop of negative keccak
    rule chop (0 -Int keccak(BA)) => pow256 -Int keccak(BA)
       [simplification]
```

5. Ensure that any value resulting from a `keccak` is within the valid range of 0 and 2^256 - 1.

```k
    // keccak cannot equal a number outside of its range
    rule { X #Equals keccak (_) } => #Bottom
      requires X <Int 0 orBool X >=Int pow256
      [concrete(X), simplification]

    rule keccak(B:Bytes) <Int BOUND:Int => true requires BOUND >=Int pow256 -Int 32 [simplification, concrete(BOUND)]

endmodule
```