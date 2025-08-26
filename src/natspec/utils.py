from __future__ import annotations

from typing import TYPE_CHECKING

from pyk.kast.inner import KLabel, KSort

if TYPE_CHECKING:
    from typing import Final


# Sorts
ID: Final[KSort] = KSort('Id')
STRUCTFIELD: Final[KSort] = KSort('SolidityStructAccess')
ARRAYACCESS: Final[KSort] = KSort('SolidityArrayAccess')

# Logical operators
NEGATION: Final[KLabel] = KLabel('SolidityNegation')
CONJUNCTION: Final[KLabel] = KLabel('SolidityConjunction')
DISJUNCTION: Final[KLabel] = KLabel('SolidityDisjunction')

# Arithmetic operators
MULTIPLICATION: Final[KLabel] = KLabel('SolidityMultiplication')
DIVISION: Final[KLabel] = KLabel('SolidityDivision')
ADDITION: Final[KLabel] = KLabel('SolidityAddition')
SUBTRACTION: Final[KLabel] = KLabel('SoliditySub')

# Comparison operators
LESS_THAN: Final[KLabel] = KLabel('SolidityLT')
LESS_THAN_OR_EQUAL: Final[KLabel] = KLabel('SolidityLE')
GREATER_THAN: Final[KLabel] = KLabel('SolidityGT')
GREATER_THAN_OR_EQUAL: Final[KLabel] = KLabel('SolidityGE')
EQUAL: Final[KLabel] = KLabel('SolidityEq')
NOT_EQUAL: Final[KLabel] = KLabel('SolidityNeq')

NATSPEC_TO_K_OPERATORS: Final[dict[KLabel, KLabel]] = {
    NEGATION: KLabel('notBool_'),
    CONJUNCTION: KLabel('_andBool_'),
    DISJUNCTION: KLabel('_orBool_'),
    MULTIPLICATION: KLabel('_*Int_'),
    DIVISION: KLabel('_divInt_'),
    ADDITION: KLabel('_+Int_'),
    SUBTRACTION: KLabel('_-Int_'),
    LESS_THAN: KLabel('_<Int_'),
    LESS_THAN_OR_EQUAL: KLabel('_<=Int_'),
    GREATER_THAN: KLabel('_>Int_'),
    GREATER_THAN_OR_EQUAL: KLabel('_>=Int_'),
    EQUAL: KLabel('_==Int_'),
    NOT_EQUAL: KLabel('_=/=Int_'),
}
