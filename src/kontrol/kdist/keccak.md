Keccak Assumptions
==============

The provided K Lemmas define assumptions and properties related to the `keccak` hash function used in the verification of smart contracts within the symbolic execution context.

```k
module KECCAK-LEMMAS
    imports FOUNDRY
    imports INT-SYMBOLIC
```

1. `keccak` always returns an integer in the range `[0, 2 ^ 256)`.

```k
    rule 0 <=Int keccak( _ )             => true [simplification, smt-lemma]
    rule         keccak( _ ) <Int pow256 => true [simplification, smt-lemma]
```

2. No value outside of the `[0, 2 ^ 256)` range can be the result of a `keccak`.

```k
    rule [keccak-out-of-range]:      X  ==Int  keccak (_)   => false   requires X <Int 0 orBool X >=Int pow256 [concrete(X), simplification]
    rule [keccak-out-of-range-ml]: { X #Equals keccak (_) } => #Bottom requires X <Int 0 orBool X >=Int pow256 [concrete(X), simplification]
```

3. This lemma directly simplifies an expression that involves a `keccak` and is often introduced by the Solidity compiler.

```k
    rule chop (0 -Int keccak(BA)) => pow256 -Int keccak(BA)
       [simplification]
```

4. The result of a `keccak` is assumed not to fall too close to the edges of its official range. This accounts for the shifts added to the result of a `keccak` when accessing storage slots, and is a hypothesis made by the ecosystem.

```k
    rule BOUND:Int <Int keccak(B:Bytes) => true requires BOUND <=Int 32             [simplification, concrete(BOUND)]
    rule keccak(B:Bytes) <Int BOUND:Int => true requires BOUND >=Int pow256 -Int 32 [simplification, concrete(BOUND)]
```

5. `keccak` is injective: that is, if `keccak(A)` equals `keccak(B)`, then `A` equals `B`.

In reality, cryptographic hash functions like `keccak` are not injective. They are designed to be collision-resistant, meaning it is computationally infeasible to find two different inputs that produce the same hash output, but not impossible.
This assumption reflects that hypothesis in the context of formal verification, making it more tractable.

```k
    rule [keccak-inj]:      keccak(A)  ==Int  keccak(B)   =>                A ==K B   [simplification]
    rule [keccak-inj-ml]: { keccak(A) #Equals keccak(B) } => { true #Equals A ==K B } [simplification]
```

6. `keccak` of a symbolic parameter does not equal a concrete value. This lemma is based on our experience in Foundry-supported testing and is specific to how `keccak` functions are used in practical symbolic execution. The underlying hypothesis that justifies it is that the storage slots of a given mapping are presumed to be disjoint from slots of other mappings and also the non-mapping slots of a contract.

```k
    rule [keccak-eq-conc-false]: keccak(_A)  ==Int _B => false [symbolic(_A), concrete(_B), simplification(30), comm]
    rule [keccak-neq-conc-true]: keccak(_A) =/=Int _B => true  [symbolic(_A), concrete(_B), simplification(30), comm]

    rule [keccak-eq-conc-false-ml-lr]: { keccak(A) #Equals B } => { true #Equals keccak(A) ==Int B } [symbolic(A), concrete(B), simplification]
    rule [keccak-eq-conc-false-ml-rl]: { B #Equals keccak(A) } => { true #Equals keccak(A) ==Int B } [symbolic(A), concrete(B), simplification]
```

```k
endmodule
```