from __future__ import annotations

from typing import TYPE_CHECKING

from pyk.kast.inner import KApply, KLabel, KSort, KToken

if TYPE_CHECKING:
    from typing import Final


# Sorts
ID: Final[KSort] = KSort('Id')
ACCESS: Final[KSort] = KSort('Access')
HEX_LITERAL: Final[KSort] = KSort('HexLiteral')
EXP: Final[KSort] = KSort('Exp')

# Access operators
INDEX_ACCESS: Final[KLabel] = KLabel('SolidityIndexAccess')
FIELD_ACCESS: Final[KLabel] = KLabel('SolidityFieldAccess')

# Unary operators
NEGATION: Final[KLabel] = KLabel('SolidityNegation')

# Binary arithmetic operators
POWER: Final[KLabel] = KLabel('SolidityPower')
MULTIPLICATION: Final[KLabel] = KLabel('SolidityMultiplication')
DIVISION: Final[KLabel] = KLabel('SolidityDivision')
MODULO: Final[KLabel] = KLabel('SolidityModulo')
ADDITION: Final[KLabel] = KLabel('SolidityAddition')
SUBTRACTION: Final[KLabel] = KLabel('SoliditySub')

# Comparison operators
LESS_THAN: Final[KLabel] = KLabel('SolidityLT')
LESS_THAN_OR_EQUAL: Final[KLabel] = KLabel('SolidityLE')
GREATER_THAN: Final[KLabel] = KLabel('SolidityGT')
GREATER_THAN_OR_EQUAL: Final[KLabel] = KLabel('SolidityGE')
EQUAL: Final[KLabel] = KLabel('SolidityEq')
NOT_EQUAL: Final[KLabel] = KLabel('SolidityNeq')

# Logical operators
CONJUNCTION: Final[KLabel] = KLabel('SolidityConjunction')
DISJUNCTION: Final[KLabel] = KLabel('SolidityDisjunction')

NATSPEC_TO_K_OPERATORS: Final[dict[KLabel, KLabel]] = {
    NEGATION: KLabel('notBool_'),
    POWER: KLabel('_^Int_'),
    MULTIPLICATION: KLabel('_*Int_'),
    DIVISION: KLabel('_divInt_'),
    MODULO: KLabel('_modInt_'),
    ADDITION: KLabel('_+Int_'),
    SUBTRACTION: KLabel('_-Int_'),
    LESS_THAN: KLabel('_<Int_'),
    LESS_THAN_OR_EQUAL: KLabel('_<=Int_'),
    GREATER_THAN: KLabel('_>Int_'),
    GREATER_THAN_OR_EQUAL: KLabel('_>=Int_'),
    EQUAL: KLabel('_==Int_'),
    NOT_EQUAL: KLabel('_=/=Int_'),
    CONJUNCTION: KLabel('_andBool_'),
    DISJUNCTION: KLabel('_orBool_'),
}

BLOCK_TIMESTAMP: Final[KApply] = KApply(FIELD_ACCESS, [KToken('block', sort=ID), KToken('timestamp', sort=ID)])
BLOCK_NUMBER: Final[KApply] = KApply(FIELD_ACCESS, [KToken('block', sort=ID), KToken('number', sort=ID)])
BLOCK_COINBASE: Final[KApply] = KApply(FIELD_ACCESS, [KToken('block', sort=ID), KToken('coinbase', sort=ID)])
BLOCK_DIFFICULTY: Final[KApply] = KApply(FIELD_ACCESS, [KToken('block', sort=ID), KToken('difficulty', sort=ID)])

MSG_SENDER: Final[KApply] = KApply(FIELD_ACCESS, [KToken('msg', sort=ID), KToken('sender', sort=ID)])
MSG_DATA: Final[KApply] = KApply(FIELD_ACCESS, [KToken('msg', sort=ID), KToken('data', sort=ID)])
MSG_VALUE: Final[KApply] = KApply(FIELD_ACCESS, [KToken('msg', sort=ID), KToken('value', sort=ID)])

GLOBAL_VARIABLES_TO_CELL_NAMES: Final[dict[KApply, str]] = {
    BLOCK_TIMESTAMP: 'TIMESTAMP_CELL',
    BLOCK_NUMBER: 'NUMBER_CELL',
    BLOCK_COINBASE: 'COINBASE_CELL',
    BLOCK_DIFFICULTY: 'DIFFICULTY_CELL',
    MSG_SENDER: 'CALLER_CELL',
    MSG_DATA: 'CALLDATA_CELL',
    MSG_VALUE: 'CALLVALUE_CELL',
}
