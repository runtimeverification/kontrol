Solidity Natspec Grammar
------------------------


 TODO:
 ----
 1. add support for nested access.(i.e. `x[1][2]`, `keys[1].value`)
 2. `ArrayAccess` should also accept vars as indexes. (i.e.`x[a]` )
 3. add support for Bytes sort
 4. add support for bitwise operators

```k
module NATSPEC-SYNTAX
    imports INT-SYNTAX
    imports BOOL-SYNTAX
    imports ID-SYNTAX

    syntax StructField ::= Id "." Id [symbol(SolidityStructAccess)]
    syntax ArrayAccess ::= Id "[" Int "]" [symbol(SolidityArrayAccess)]
    syntax SolidityId ::= Id | StructField | ArrayAccess

    syntax Exp ::= Int | Bool | SolidityId
                 | "(" Exp ")"  [bracket]
                 > "!" Exp      [symbol(SolidityNegation)]
                 > left:
                   Exp "*" Exp  [symbol(SolidityMultiplication)]
                 | Exp "/" Exp  [symbol(SolidityDivision)]
                 > left:
                   Exp "+" Exp  [symbol(SolidityAddition)]
                 | Exp "-" Exp  [symbol(SoliditySub)]
                 > non-assoc:
                   Exp "<" Exp  [symbol(SolidityLT)]
                 | Exp "<=" Exp [symbol(SolidityLE)]
                 | Exp ">" Exp  [symbol(SolidityGT)]
                 | Exp ">=" Exp [symbol(SolidityGE)]
                 | Exp "==" Exp [symbol(SolidityEq)]
                 | Exp "!=" Exp [symbol(SolidityNeq)]
                 > left:
                   Exp "&&" Exp [symbol(SolidityConjunction)]
                 | Exp "||" Exp [symbol(SolidityDisjunction)]
endmodule

module NATSPEC
endmodule
```