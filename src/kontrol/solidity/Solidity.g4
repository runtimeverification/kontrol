grammar Solidity;

// Parser rules
expression
    : booleanExpression
    ;

booleanExpression
    : booleanExpression '&&' booleanExpression        # AndExpression
    | booleanExpression '||' booleanExpression        # OrExpression
    | '!' booleanExpression                           # NotExpression
    | arithmeticExpression RelOp arithmeticExpression # RelationalExpression
    | BOOLEAN_LITERAL                                 # BooleanLiteral
    | '(' booleanExpression ')'                       # ParenthesizedBooleanExpression
    ;

arithmeticExpression
    : arithmeticExpression '+' arithmeticExpression   # AddExpression
    | arithmeticExpression '-' arithmeticExpression   # SubtractExpression
    | arithmeticExpression '*' arithmeticExpression   # MultiplyExpression
    | arithmeticExpression '/' arithmeticExpression   # DivideExpression
    | atom                                            # AtomExpression
    ;

atom
    : VariableName                                    # Variable
    | LengthAccess                                    # LengthAccess
    | ArrayElement                                    # ArrayElement
    | MappingElement                                  # MappingElement
    | AddressLiteral                                  # AddressLiteral
    | INTEGER                                         # IntegerLiteral
    | '(' arithmeticExpression ')'                    # ParenthesizedArithmeticExpression
    | BlockAccess                                     # BlockAccess
    | MsgAccess                                       # MsgAccess
    ;

// Lexer rules
BOOLEAN_LITERAL: 'true' | 'false';
INTEGER: [0-9]+;
ADDRESS: '0x' [0-9a-fA-F]+;

VariableName: [a-zA-Z_][a-zA-Z0-9_]*;
LengthAccess: VariableName '.length';
ArrayElement: VariableName '[' INTEGER ']';
MappingElement: VariableName '[' VariableName ']';
AddressLiteral: ADDRESS;
BlockAccess: 'block.' ('timestamp' | 'number');
MsgAccess: 'msg.' ('sender');

RelOp: '<' | '<=' | '>' | '>=' | '==' | '!=';

// Whitespace and comments
WS: [ \t\r\n]+ -> skip;