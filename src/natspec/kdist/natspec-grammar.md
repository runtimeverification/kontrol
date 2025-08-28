Solidity Natspec Grammar
------------------------


 TODO:
 ----
 1. add support for bitwise operators

```k
module NATSPEC-SYNTAX
    imports INT-SYNTAX
    imports BOOL-SYNTAX
    imports ID-SYNTAX

    // Literals
    syntax HexLiteral ::= r"0x[0-9a-fA-F]+" [token, symbol(SolidityHexLiteral)]
 // ---------------------------------------------------------------------------

    syntax Access ::= Id
                    | Access "[" Exp "]" [symbol(SolidityIndexAccess)]
                    | Access "." Id      [symbol(SolidityFieldAccess)]
 // ------------------------------------------------------------------

    syntax Exp ::= Int | Bool | HexLiteral | Access
                 | "(" Exp ")"                   [bracket]
                 // Unary operators (high precedence)
                 > "!" Exp                       [symbol(SolidityNegation)]
                 // Power (right associative)
                 > right:
                   Exp "**" Exp                  [symbol(SolidityPower)]
                 // Multiplicative
                 > left:
                   Exp "*" Exp                   [symbol(SolidityMultiplication)]
                 | Exp "/" Exp                   [symbol(SolidityDivision)]
                 | Exp "%" Exp                   [symbol(SolidityModulo)]
                 // Additive
                 > left:
                   Exp "+" Exp                   [symbol(SolidityAddition)]
                 | Exp "-" Exp                   [symbol(SoliditySubtraction)]
                 // Relational
                 > non-assoc:
                   Exp "<" Exp                   [symbol(SolidityLT)]
                 | Exp ">" Exp                   [symbol(SolidityGT)]
                 | Exp "<=" Exp                  [symbol(SolidityLE)]
                 | Exp ">=" Exp                  [symbol(SolidityGE)]
                 // Equality
                 > non-assoc:
                   Exp "==" Exp                  [symbol(SolidityEq)]
                 | Exp "!=" Exp                  [symbol(SolidityNeq)]
                 // Logical AND
                 > left:
                   Exp "&&" Exp                  [symbol(SolidityConjunction)]
                 // Logical OR
                 > left:
                   Exp "||" Exp                  [symbol(SolidityDisjunction)]
endmodule

module NATSPEC
endmodule
```