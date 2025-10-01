"""Counterexample test generation for Kontrol (refactored).

This module extracts concrete counterexample values from a failed APR proof
and produces a Forge (Foundry) Solidity test that reproduces the issue.

"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Optional

from pyk.proof.reachability import APRFailureInfo

if TYPE_CHECKING:
    from pathlib import Path

    from pyk.proof.reachability import APRProof

    from .foundry import Foundry

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedTestId:
    """Structured information derived from a Kontrol test/proof id.

    Examples of incoming ids:
        - "test%SimpleStorageTest.test_storage_setup(...):0"
        - "SimpleStorageTest.test_storage_setup(...):0"
    """

    raw: str
    contract_name: str
    method_name: str
    clean_test_id: str
    test_contract_id: str


def generate_counterexample_test(
    proof: APRProof,
    foundry: Foundry,
    output_dir: Optional[Path] = None,
) -> Optional[Path]:
    _LOGGER.info(f'Starting counterexample generation for proof: {proof.id}')
    failure_info = getattr(proof, 'failure_info', None)
    if not isinstance(failure_info, APRFailureInfo):
        _LOGGER.warning('Proof failure info is not APRFailureInfo, cannot generate counterexample')
        return None
    if not failure_info.failing_nodes:
        _LOGGER.warning('No failing nodes available for counterexample generation')
        return None

    parsed = _parse_test_id(proof.id)
    _LOGGER.info(f'Parsed test ID: {parsed}')
    method = _try_get_contract_method(foundry, parsed)

    # Must find the original test file or bail.
    original_test_file = _find_original_test_file(foundry, parsed)
    _LOGGER.info(f'Found original test file: {original_test_file}')
    if not (original_test_file and original_test_file.exists()):
        _LOGGER.warning(
            'Counterexample generation failed: could not locate original test file for %s',
            proof.id,
        )
        return None

    # Set output directory to same as original test file
    if output_dir is None:
        output_dir = original_test_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f'{parsed.contract_name}CounterexampleTest.t.sol'

    # Copy original test file to counterexample file if it doesn't exist
    original_src: str = ''
    if not out_path.exists():
        try:
            original_src = original_test_file.read_text(encoding='utf-8')
            out_path.write_text(original_src, encoding='utf-8')
            _LOGGER.info('Copied original test file to %s', out_path)
        except Exception as e:
            _LOGGER.warning('Failed to copy original test file: %s', e)
            return None

    # Determine continuing index per base method in case there's more than one counterexample
    start_idx = _next_ce_index_start(out_path, parsed.method_name)

    # Iterate through all failing nodes and generate a function for each
    node_ids = sorted(failure_info.failing_nodes)
    functions: list[str] = []
    for i, node_id in enumerate(node_ids):
        model = failure_info.models.get(node_id)
        if not model:
            _LOGGER.warning('No model for failing node %r; skipping', node_id)
            continue

        concrete_values = _extract_concrete_values(model, method)
        new_method_name = f'{parsed.method_name}_ce{start_idx + i}'

        # Extract the original function, rename it, and insert assignments at the top
        fn_src = _extract_and_modify_function(
            content=original_src,
            original_method_name=parsed.method_name,
            new_method_name=new_method_name,
            concrete_values=concrete_values,
            method=method,
        )
        functions.append(fn_src)
        _LOGGER.info('Prepared counterexample function clone (%s, node=%s)', new_method_name, node_id)

    if not functions:
        _LOGGER.warning('No functions generated for %s (no models matched)', proof.id)
        return out_path

    # Append cloned functions into the original contract before its closing brace
    ok = _append_functions_to_original_contract(out_path, parsed.contract_name, functions)
    if not ok:
        _LOGGER.warning('Counterexample generation failed: could not append functions into %s', out_path)
        return None

    _LOGGER.info('Appended %d function(s) to %s', len(functions), out_path)
    return out_path


def _parse_test_id(test_id: str) -> ParsedTestId:
    """Normalize a Kontrol test/proof id to a structured form.

    - Replaces '%' with '/' for path-like splits but ultimately extracts the
      final "Contract.function(...):version" segment.
    - Strips ":<version>" suffix and "(…)" parameter list from the method.
    """
    # Keep raw for diagnostics
    raw = test_id

    # Extract tail segment after the final '/' or '%'
    sep_idx = max(raw.rfind('/'), raw.rfind('%'))
    tail = raw[sep_idx + 1 :] if sep_idx >= 0 else raw

    # Split contract and method portion
    try:
        contract_and_method = tail
        contract, method = contract_and_method.split('.', 1)
    except ValueError as exc:  # no '.' separator
        raise ValueError(f'Unrecognized test id format: {test_id!r}') from exc

    # Remove version suffix ":N" if present
    if ':' in method:
        method = method.rsplit(':', 1)[0]

    # Remove parameter list if present
    if '(' in method:
        method = method.split('(', 1)[0]

    clean_test_id = f'{contract}.{method}'
    test_contract_id = f'test%{contract}.{method}'

    return ParsedTestId(
        raw=raw,
        contract_name=contract,
        method_name=method,
        clean_test_id=clean_test_id,
        test_contract_id=test_contract_id,
    )


def _try_get_contract_method(foundry: Foundry, parsed: ParsedTestId) -> Optional[Any]:
    """Try to resolve (contract, method) via Foundry metadata.

    Returns the *method* object (if any) so that we can read parameter names/types.
    """
    try:
        _contract, method = foundry.get_contract_and_method(parsed.clean_test_id)
        return method
    except KeyError:
        try:
            _contract, method = foundry.get_contract_and_method(parsed.test_contract_id)
            return method
        except KeyError:
            return None


def _extract_concrete_values(
    model: Iterable[tuple[str, str]],
    method: Optional[Any],
) -> dict[str, Any]:
    """Extract concrete parameter values from a model.

    If method*is known, we map symbolic variable names (e.g., KV0_totalSupply)
    to canonical parameter names (including leading underscores). Otherwise we
    attempt a best-effort extraction by parsing KV*_suffix tokens.
    """
    concrete: dict[str, Any] = {}

    if method is None:
        for var, term in model:
            if var.startswith('KV') and '_' in var:
                # KV0_totalSupply:Int -> totalSupply
                suffix = var.split('_', 1)[1]
                param_name = suffix.split(':', 1)[0]
                value = _convert_term_to_value(term)
                if value is not None:
                    concrete[param_name] = value
        return concrete

    # Build var->param mapping from ABI-like info
    var_to_param: dict[str, str] = {}
    inputs = getattr(method, 'inputs', None)
    if inputs is not None:
        for inp in list(inputs):
            arg_name = getattr(inp, 'arg_name', None)
            name = getattr(inp, 'name', None)
            if arg_name and name:
                var_to_param[arg_name] = name

    for var, term in model:
        if var in var_to_param:
            pname = var_to_param[var]
            value = _convert_term_to_value(term)
            if value is not None:
                concrete[pname] = value

    return concrete


def _find_original_test_file(foundry: Foundry, parsed: ParsedTestId) -> Optional[Path]:
    """Find the original test file using the test ID path.

    The test ID contains path information with % as separator, which we convert to /.
    """
    # Convert % to / in the raw test ID to get the file path
    test_path = parsed.raw.replace('%', '/')

    # Remove the version suffix and parameter list to get just the file path
    if ':' in test_path:
        test_path = test_path.rsplit(':', 1)[0]
    if '(' in test_path:
        test_path = test_path.rsplit('(', 1)[0]

    # Remove the function name to get just the directory path
    # e.g., "test/UnitTest.test_counterexample" -> "test/UnitTest"
    if '.' in test_path:
        test_path = test_path.rsplit('.', 1)[0]

    # The issue is that the contract name in the test ID might not match the file name
    # For example: "test/UnitTest" should map to "test/Unit.t.sol"
    # Let's try to find the file by searching for the contract name in the test directory
    test_dir = foundry._root / 'test'
    if not test_dir.exists():
        return None

    # Search for files containing the contract name
    candidates = list(test_dir.rglob('*.t.sol')) + list(test_dir.rglob('*.sol'))

    for candidate in candidates:
        try:
            text = candidate.read_text(encoding='utf-8')
            if f'contract {parsed.contract_name}' in text:
                return candidate
        except Exception:
            continue

    return None


_ASSIGNMENT_MARKER = '// Counterexample values from failed proof:'


def _extract_and_modify_function(
    *,
    content: str,
    original_method_name: str,
    new_method_name: str,
    concrete_values: dict[str, Any],
    method: Optional[Any],
) -> str:
    """Extract a function from the original file, rename it, and insert assignments at the top."""

    # First, get the modified content with assignments injected
    modified_content = _insert_assignments_into_function(
        content=content,
        method_name=original_method_name,
        method=method,
        concrete_values=concrete_values,
    )

    # Extract just the modified function
    sig_re = re.compile(
        rf'(function\s+{re.escape(original_method_name)}\s*\([^)]*\)[^{{]*\{{[^}}]*\}})',
        re.DOTALL,
    )
    m = sig_re.search(modified_content)
    if not m:
        raise ValueError(f'Could not locate function {original_method_name} in source.')

    func_text = m.group(1)

    # Rename the function
    func_text = re.sub(
        rf'function\s+{re.escape(original_method_name)}\s*\(',
        f'function {new_method_name}(',
        func_text,
        count=1,
    )

    indented_func = '    ' + func_text.replace('\n', '\n    ')
    return '\n' + indented_func + '\n'


def _insert_assignments_into_function(
    *,
    content: str,
    method_name: str,
    method: Optional[Any],
    concrete_values: dict[str, Any],
) -> str:
    """Insert assignments at the beginning of the actual function body.

    Robust to modifiers (public view returns (...) virtual override ...),
    line breaks, and spacing. Idempotent per-function via _ASSIGNMENT_MARKER.
    """
    text = content

    # 1) Find the start of the target function signature: `function <name>(`
    sig_needle = f'function {method_name}('
    sig_pos = text.find(sig_needle)
    if sig_pos == -1:
        # Try a looser search tolerating extra spaces/newlines between tokens
        m = re.search(rf'\bfunction\s+{re.escape(method_name)}\s*\(', text)
        if not m:
            return text
        sig_pos = m.start()

    # 2) From the first '(' after the method name, find the matching ')'
    paren_start = text.find('(', sig_pos)
    if paren_start == -1:
        return text

    depth = 0
    i = paren_start
    while i < len(text):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                break
        i += 1
    if i >= len(text) or depth != 0:
        return text
    paren_end = i  # index of the closing ')'

    # 3) After the signature, skip whitespace/modifiers until the opening '{'
    j = paren_end + 1
    while j < len(text) and text[j].isspace():
        j += 1

    # Skip modifier/returns tokens until '{'
    # (We don't try to parse them; just scan until first '{')
    brace_pos = text.find('{', j)
    if brace_pos == -1:
        return text

    # 4) Find the end of the function by brace counting from this '{'
    depth = 0
    k = brace_pos
    while k < len(text):
        if text[k] == '{':
            depth += 1
        elif text[k] == '}':
            depth -= 1
            if depth == 0:
                break
        k += 1
    if k >= len(text) or depth != 0:
        return text
    func_start = sig_pos
    func_body_open = brace_pos
    func_end = k  # index of the matching closing '}'

    # 5) Extract params to map assignments
    params_segment = text[paren_start + 1 : paren_end].strip()
    actual_param_names: list[str] = []
    param_types: dict[str, str] = {}
    if params_segment:
        # split on commas at top level (there are no nested parens in types/names)
        for raw in [p.strip() for p in params_segment.split(',') if p.strip()]:
            parts = raw.split()
            if len(parts) >= 2:
                ptype = parts[0]
                pname = parts[-1]
                actual_param_names.append(pname)
                param_types[pname] = ptype

    # 6) Build assignment lines
    def _lookup_value(name: str) -> Optional[Any]:
        if name in concrete_values:
            return concrete_values[name]
        if name.startswith('_') and name[1:] in concrete_values:
            return concrete_values[name[1:]]
        alt = f'_{name}'
        if alt in concrete_values:
            return concrete_values[alt]
        return None

    assignments: list[str] = []
    for pname in actual_param_names:
        v = _lookup_value(pname)
        if v is None:
            continue
        ptype = param_types.get(pname, 'uint256')
        assignments.append(f'        {pname} = {_format_value(v, ptype)};')

    if not assignments:
        # Nothing to insert; keep function unchanged
        return text

    # 7) Idempotence: if marker already inside this function, do nothing
    func_block = text[func_start : func_end + 1]
    if _ASSIGNMENT_MARKER in func_block:
        return text

    # 8) Insert assignments right after the opening '{'
    insert_block = '        ' + _ASSIGNMENT_MARKER + '\n' + '\n'.join(assignments) + '\n'
    new_text = text[: func_body_open + 1] + '\n' + insert_block + text[func_body_open + 1 :]

    return new_text


def _next_ce_index_start(out_path: Path, base_method_name: str) -> int:
    try:
        text = out_path.read_text(encoding='utf-8')
    except Exception:
        return 0
    pat = re.compile(rf'function\s+{re.escape(base_method_name)}_ce(\d+)\s*\(')
    nums = [int(m.group(1)) for m in pat.finditer(text)]
    return (max(nums) + 1) if nums else 0


def _append_functions_to_original_contract(
    out_path: Path,
    contract_name: str,
    functions: list[str],
) -> bool:
    """Insert functions before the final '}' of the original contract.
    Returns True on success, False on failure (malformed file, etc.).
    """
    try:
        text = out_path.read_text(encoding='utf-8')
    except Exception:
        return False

    # Look for the original contract using regex to handle inheritance, modifiers, etc.
    import re

    # Pattern to match: contract ContractName [anything] {
    contract_pattern = rf'contract\s+{re.escape(contract_name)}\s+[^{{]*\{{'
    if not re.search(contract_pattern, text):
        _LOGGER.warning('Could not find contract %s in %s', contract_name, out_path)
        return False

    # Find the last closing brace of the contract
    last_brace = text.rfind('}')
    if last_brace == -1:
        return False

    # Join functions with proper spacing
    functions_text = '\n'.join(functions)
    new_text = text[:last_brace] + '\n' + functions_text + '\n' + text[last_brace:]
    try:
        out_path.write_text(new_text, encoding='utf-8')
        return True
    except Exception:
        return False


_int_token_re = re.compile(r'^(-?\d+)(?::Int)?$')
_bool_token_re = re.compile(r'^(true|false)(?::Bool)?$', re.IGNORECASE)
_hex_re = re.compile(r'^0x[0-9a-fA-F]+$')
_addr_token_re = re.compile(r'^(0x[0-9a-fA-F]+|-?\d+):Addr$')


def _convert_term_to_value(term: str) -> Any:
    """Convert a K term string into a concrete Python value usable in Solidity.

    Handles ints, bools, hex strings, and simple address encodings.
    Returns None on unknown formats.
    """
    t = term.strip()

    # int or Int token
    m = _int_token_re.match(t)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None

    # plain hex literal
    if _hex_re.match(t):
        return t

    # bool or Bool token
    m = _bool_token_re.match(t)
    if m:
        return m.group(1).lower() == 'true'

    # quoted string
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        return t[1:-1]

    # Addr token: decimal or hex -> hex string
    m = _addr_token_re.match(t)
    if m:
        raw = m.group(1)
        if raw.startswith('0x'):
            return raw
        try:
            return hex(int(raw))
        except ValueError:
            return None

    _LOGGER.warning('Could not convert term to concrete value: %r', term)
    return None


def _format_value(value: Any, param_type: str) -> str:
    """Format a concrete value as a Solidity literal for the given param type."""
    # bool
    if param_type == 'bool':
        if isinstance(value, bool):
            return 'true' if value else 'false'
        if isinstance(value, int):
            return 'true' if value != 0 else 'false'
        return 'false'

    # address
    if param_type == 'address':
        if isinstance(value, str) and _hex_re.match(value):
            return f'address({value})'
        if isinstance(value, int):
            return 'address(0)' if value == 0 else f'address({hex(value)})'
        return 'address(0)'

    # bytes / string (very basic handling)
    if param_type == 'string':
        if isinstance(value, str):
            return value if value.startswith('"') else f'{value!r}'
        return '""'
    if param_type == 'bytes':
        if isinstance(value, str) and _hex_re.match(value):
            return value
        return '""'

    # numeric fallbacks
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value if value.startswith('0x') else repr(value)

    return str(value)
