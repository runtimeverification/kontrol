from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from antlr4.CommonTokenStream import CommonTokenStream
from antlr4.InputStream import InputStream as ANTLRInputStream
from kevm_pyk.kevm import KEVM
from pyk.kast.inner import KApply, KLabel, KVariable
from pyk.kast.manip import flatten_label
from pyk.kast.prelude.ml import mlEqualsTrue
from pyk.kast.prelude.utils import token
from pyk.utils import single
from sgp.ast_node_types import (  # type: ignore
    BinaryOperation,
    Identifier,
    IndexAccess,
    MemberAccess,
    NumberLiteral,
    UnaryOperation,
)
from sgp.parser.SolidityLexer import SolidityLexer  # type: ignore
from sgp.parser.SolidityParser import SolidityParser  # type: ignore
from sgp.sgp_visitor import SGPVisitor, SGPVisitorOptions  # type: ignore

from .solc_to_k import Contract

if TYPE_CHECKING:
    from typing import Final

    from pyk.cterm import CTerm
    from pyk.kast.inner import KInner, KToken

    from .foundry import Foundry

_LOGGER: Final = logging.getLogger(__name__)

# K Int Operators: https://github.com/runtimeverification/k/blob/master/k-distribution/include/kframework/builtin/domains.md?plain=1#L1223
# Solidity operators: https://docs.soliditylang.org/en/v0.8.30/types.html
SGP_TO_K_OPERATORS: Final[dict[str, KLabel]] = {
    # Arithmetic operators
    '+': KLabel('_+Int_'),
    '-': KLabel('_-Int_'),
    '*': KLabel('_*Int_'),
    '/': KLabel('_/Int_'),  # t-division (rounds towards zero)
    '%': KLabel('_%Int_'),  # t-modulus
    '**': KLabel('_^Int_'),  # exponentiation
    # Comparison operators
    '<': KLabel('_<Int_'),
    '<=': KLabel('_<=Int_'),
    '>': KLabel('_>Int_'),
    '>=': KLabel('_>=Int_'),
    '==': KLabel('_==Int_'),
    '!=': KLabel('_=/=Int_'),
    # Boolean operators
    '&&': KLabel('_andBool_'),
    '||': KLabel('_orBool_'),
    '!': KLabel('notBool_'),
    # Bitwise operators
    '&': KLabel('_&Int_'),  # bitwise AND
    '|': KLabel('_|Int_'),  # bitwise OR
    '^': KLabel('_xorInt_'),  # bitwise XOR
    '<<': KLabel('_<<Int_'),  # left shift
    '>>': KLabel('_>>Int_'),  # right shift
    '~': KLabel('~Int_'),  # bitwise NOT (unary)
}


GLOBAL_VARIABLES_TO_CELL_NAMES: Final[dict[tuple[str, str], str]] = {
    ('block', 'timestamp'): 'TIMESTAMP_CELL',
    ('block', 'number'): 'NUMBER_CELL',
    ('block', 'coinbase'): 'COINBASE_CELL',
    ('block', 'difficulty'): 'DIFFICULTY_CELL',
    ('msg', 'sender'): 'CALLER_CELL',
    ('msg', 'data'): 'CALLDATA_CELL',
    ('msg', 'value'): 'CALLVALUE_CELL',
}

# https://docs.soliditylang.org/en/v0.8.30/units-and-global-variables.html
UNIT_MULTIPLIERS: Final[dict[str, int]] = {
    # Ether units
    'wei': 1,
    'gwei': 10**9,
    'ether': 10**18,
    # Time units
    'seconds': 1,
    'minutes': 60,
    'hours': 3600,
    'days': 86400,
    'weeks': 604800,
}


def apply_natspec_preconditions(
    cterm: CTerm, method: Contract.Method | Contract.Constructor, contract: Contract, foundry: Foundry
) -> CTerm:
    """Apply preconditions from method Natspec documentation to the CTerm."""

    if type(method) is Contract.Method:
        precondition_constraints = extract_precondition_constraints(method, cterm, contract)

        for precondition in precondition_constraints:
            _LOGGER.info(f'Adding NatSpec precondition: {foundry.kevm.pretty_print(mlEqualsTrue(precondition))}')
            cterm = cterm.add_constraint(mlEqualsTrue(precondition))
    return cterm


def extract_precondition_constraints(method: Contract.Method, init_cterm: CTerm, contract: Contract) -> list[KInner]:
    """Extract constraints from method's NatSpec preconditions."""

    precondition_constraints: list[KInner] = []

    if method.preconditions is not None:
        for p in method.preconditions:
            ast = parse_solidity_expression(p.precondition)
            if ast:
                kontrol_precondition = sgp_ast_to_kast(ast, method, init_cterm, contract)
                if kontrol_precondition:
                    precondition_constraints.append(kontrol_precondition)

    return precondition_constraints


def parse_solidity_expression(precondition_text: str) -> Any:
    """Parse a Solidity expression string using SGP and return the AST."""
    try:
        input_stream = ANTLRInputStream(precondition_text)
        lexer = SolidityLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = SolidityParser(token_stream)
        parse_tree = parser.expression()

        visitor = SGPVisitor(SGPVisitorOptions())
        ast = visitor.visit(parse_tree)
        return ast
    except Exception as e:
        _LOGGER.warning(f'Failed to parse precondition with SGP: {precondition_text}, error: {e}')
        return None


def sgp_ast_to_kast(node: Any, method: Contract.Method, init_cterm: CTerm, contract: Contract) -> KInner | None:
    """Convert an AST node parsed with SGP to a Kontrol kast term."""
    match node:
        case BinaryOperation():
            # Map SGP operator to K operator
            k_operator = SGP_TO_K_OPERATORS.get(node.operator)
            if not k_operator:
                _LOGGER.warning(f'Unsupported binary operator: {node.operator}')
                return None

            left = sgp_ast_to_kast(node.left, method, init_cterm, contract)
            right = sgp_ast_to_kast(node.right, method, init_cterm, contract)

            if left is None or right is None:
                return None

            return KApply(k_operator, [left, right])

        case UnaryOperation():
            k_operator = SGP_TO_K_OPERATORS.get(node.operator)
            if not k_operator:
                _LOGGER.warning(f'Unsupported unary operator: {node.operator}')
                return None

            operand = sgp_ast_to_kast(node.operand, method, init_cterm, contract)
            if operand is None:
                return None

            return KApply(k_operator, [operand])

        case Identifier():
            # Check if it's a function parameter
            function_arg = method.find_arg(node.name)
            if function_arg:
                return KVariable(function_arg)

            # Check if it's a storage variable
            (storage_slot, _slot_offset) = contract.get_storage_slot_by_name(node.name)
            target_address = init_cterm.cell('ID_CELL')
            if storage_slot:
                storage_map = lookup_storage_by_address(init_cterm, target_address)
                if storage_map is None:
                    return None
                # TODO: Apply the slot offset if it's not zero.
                return KEVM.lookup(storage_map, token(storage_slot))

            _LOGGER.warning(f'SGP precondition: Unknown identifier: {node.name}')
            return None

        case MemberAccess():
            # Handle global variables (block.timestamp, msg.sender, etc.)
            if isinstance(node.expression, Identifier):
                global_var = resolve_global_variable(node.expression.name, node.member_name, init_cterm)
                if global_var:
                    return global_var
            _LOGGER.warning(f'Unsupported member access{node.expression.name}.{node.member_name}')
            return None

        case IndexAccess():
            _LOGGER.warning('Array/mapping access not supported yet')
            return None

        case NumberLiteral():
            return handle_numerical_literal(node)

        case _:
            _LOGGER.warning(f'SGP precondition: Unsupported node type: {type(node).__name__}')
            return None


def handle_numerical_literal(node: NumberLiteral) -> KToken | None:
    """Parse Solidity number literal with unit suffixes into a KToken."""

    num_str = node.number.replace('_', '').lower()
    value: int | float

    # Parse base number
    # hexadecimal
    if num_str.startswith('0x'):
        value = int(num_str, 16)
        if node.subdenomination is not None:
            _LOGGER.warning(
                f'Hexadecimal values cannot be used with unit denomination. Got {node.number} {node.subdenomination}'
            )
            return None
    # scientific notation
    elif 'e' in num_str:
        base, exp = num_str.split('e')
        value = int(float(base) * (10 ** int(exp)))
    # decimal point
    elif '.' in num_str:
        value = float(num_str)
        if node.subdenomination not in ('ether', 'gwei'):
            _LOGGER.warning(
                f"Decimal point accepted only with an 'ether' or 'gwei' subdenomination. Got {node.number} {node.subdenomination}"
            )
            return None
    else:
        value = int(num_str)

    # Apply unit multiplier if present
    if node.subdenomination:
        value *= UNIT_MULTIPLIERS.get(node.subdenomination, 1)

    return token(int(value))


def resolve_global_variable(base_name: str, member_name: str, init_cterm: CTerm) -> KInner | None:
    """Resolve Solidity global variable (e.g., msg.sender) to the according K cell value."""

    cell_name = GLOBAL_VARIABLES_TO_CELL_NAMES.get((base_name, member_name))
    if cell_name:
        return init_cterm.cell(cell_name)
    return None


def lookup_storage_by_address(cterm: CTerm, target_address: KInner) -> KInner | None:
    """Lookup storage map for account at given address."""

    accounts_cell = flatten_label('_AccountCellMap_', cterm.cell('ACCOUNTS_CELL'))
    for account_wrapped in accounts_cell:
        if not type(account_wrapped) is KApply:
            continue
        acct_id_cell = account_wrapped.terms[0]
        if not (type(acct_id_cell) is KApply and acct_id_cell.label.name == '<acctID>'):
            continue
        account_address = single(acct_id_cell.terms)
        if target_address == account_address:
            account_cell = account_wrapped.terms[1]
            if not (type(account_cell) is KApply and account_cell.label.name == '<account>'):
                continue
            storage_cell = account_cell.terms[3]
            if not (type(storage_cell) is KApply and storage_cell.label.name == '<storage>'):
                continue
            return single(storage_cell.terms)

    _LOGGER.warning(f'Account {target_address} not found in the state.')
    return None
