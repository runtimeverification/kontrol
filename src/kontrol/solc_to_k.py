from __future__ import annotations

import json
import logging
import pprint
import re
from dataclasses import dataclass
from functools import cached_property
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

from kevm_pyk.cli import KOptions
from kevm_pyk.kevm import KEVM
from pyk.cli.args import LoggingOptions
from pyk.kast.att import Atts, KAtt
from pyk.kast.inner import KApply, KLabel, KRewrite, KSort, KVariable
from pyk.kast.manip import abstract_term_safely
from pyk.kast.outer import KDefinition, KFlatModule, KImport, KNonTerminal, KProduction, KRequire, KRule, KTerminal
from pyk.kdist import kdist
from pyk.prelude.kbool import TRUE, andBool
from pyk.prelude.kint import eqInt, intToken
from pyk.prelude.string import stringToken
from pyk.utils import hash_str, run_process, single

from .cli import KGenOptions

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
    from typing import Any, Final

    from pyk.kast import KInner
    from pyk.kast.outer import KProductionItem, KSentence

_LOGGER: Final = logging.getLogger(__name__)
_PPRINT = pprint.PrettyPrinter(width=41, compact=True)


class SolcToKOptions(LoggingOptions, KOptions, KGenOptions):
    contract_file: Path
    contract_name: str


def solc_to_k(options: SolcToKOptions) -> str:
    definition_dir = kdist.get('evm-semantics.haskell')
    kevm = KEVM(definition_dir)
    empty_config = kevm.definition.empty_config(KEVM.Sorts.KEVM_CELL)

    solc_json = solc_compile(options.contract_file)
    contract_json = solc_json['contracts'][options.contract_file.name][options.contract_name]
    if 'sources' in solc_json and options.contract_file.name in solc_json['sources']:
        contract_source = solc_json['sources'][options.contract_file.name]
        for key in ['id', 'ast']:
            if key not in contract_json and key in contract_source:
                contract_json[key] = contract_source[key]
    contract = Contract(options.contract_name, contract_json, foundry=False)

    imports = list(options.imports)
    requires = list(options.requires)
    contract_module = contract_to_main_module(contract, empty_config, imports=['EDSL'] + imports)
    _main_module = KFlatModule(
        options.main_module if options.main_module else 'MAIN',
        [],
        [KImport(mname) for mname in [contract_module.name] + imports],
    )
    modules = (contract_module, _main_module)
    bin_runtime_definition = KDefinition(
        _main_module.name, modules, requires=tuple(KRequire(req) for req in ['edsl.md'] + requires)
    )

    _kprint = KEVM(definition_dir, extra_unparsing_modules=modules)
    return _kprint.pretty_print(bin_runtime_definition, unalias=False) + '\n'


@dataclass(frozen=True)
class Input:
    name: str
    type: str
    components: tuple[Input, ...] = ()
    idx: int = 0
    array_lengths: tuple[int, ...] | None = None
    dynamic_type_length: int | None = None

    @cached_property
    def arg_name(self) -> str:
        return f'V{self.idx}_{self.name.replace("-", "_")}'

    @staticmethod
    def from_dict(input: dict, idx: int = 0, natspec_lengths: dict | None = None) -> Input:
        """
        Creates an Input instance from a dictionary.

        If the optional devdocs is provided, it is used for calculating array and dynamic type lengths.
        For tuples, the function handles nested 'components' recursively.
        """
        name = input.get('name')
        type = input.get('type')
        if name is None or type is None:
            raise ValueError("ABI dictionary must contain 'name' and 'type' keys.", input)
        array_lengths, dynamic_type_length = (
            process_length_equals(input, natspec_lengths) if natspec_lengths is not None else (None, None)
        )
        if input.get('components') is not None:
            return Input(
                name,
                type,
                tuple(Input._unwrap_components(input['components'], idx, natspec_lengths)),
                idx,
                array_lengths,
                dynamic_type_length,
            )
        else:
            return Input(name, type, idx=idx, array_lengths=array_lengths, dynamic_type_length=dynamic_type_length)

    @staticmethod
    def _make_tuple_type(components: Iterable[Input], array_index: int | None = None) -> KApply:
        """
        Recursively unwraps components of a tuple and converts them to KEVM types.
        The 'array_index' parameter is used to uniquely identify elements within an array of tuples.
        """
        abi_types: list[KInner] = []
        for _c in components:
            component = _c
            if array_index is not None:
                component = Input(
                    f'{_c.name}_{array_index}',
                    _c.type,
                    _c.components,
                    _c.idx,
                    _c.array_lengths,
                    _c.dynamic_type_length,
                )
            # nested tuple, unwrap its components
            if component.type == 'tuple':
                abi_type = Input._make_tuple_type(component.components, array_index)
            else:
                abi_type = component.make_single_type()
            abi_types.append(abi_type)
        return KEVM.abi_tuple(abi_types)

    @staticmethod
    def _unwrap_components(components: list[dict], idx: int = 0, natspec_lengths: dict | None = None) -> list[Input]:
        """
        Recursively unwrap components of a complex type to create a list of Input instances.

        :param components: A list of dictionaries representing component structures
        :param idx: Starting index for components, defaults to 0
        :param natspec_lengths: Optional dictionary for calculating array and dynamic type lengths
        :return: A list of Input instances for each component, including nested components
        """
        inputs = []
        for component in components:
            lengths = process_length_equals(component, natspec_lengths) if natspec_lengths else (None, None)
            inputs.append(
                Input(
                    component['name'],
                    component['type'],
                    tuple(Input._unwrap_components(component.get('components', []), idx, natspec_lengths)),
                    idx,
                    *lengths,
                )
            )
            # If the component is of `tuple[n]` type, it will have `n` elements with different `idx`
            if component['type'].endswith('[]') and component['type'].startswith('tuple'):
                array_length, _ = lengths

                if array_length is None:
                    raise ValueError(f'Array length bounds missing for {component["name"]}')
                idx += array_length[0]
            else:
                # Otherwise, use the next `idx` for the next component
                idx += 1
        return inputs

    def make_single_type(self) -> KApply:
        """
        Generates a KApply representation for a single type input.

        It handles arrays, nested arrays, and base types.
        For 'tuple[]', it calls '_make_tuple_type' for each element in the array.
        For arrays, it generates a list of Input objects numbered from 0 to `array_length`.
        TODO: Add support for nested arrays and use the entire 'input.array_lengths' array
        instead of only the first value.
        """
        if self.type.endswith('[]'):
            base_type = self.type.rstrip('[]')
            if self.array_lengths is None:
                raise ValueError(f'Array length bounds missing for {self.name}')
            array_length = self.array_lengths[0]
            array_elements: list[KInner] = []
            if base_type == 'tuple':
                array_elements = [Input._make_tuple_type(self.components, index) for index in range(array_length)]
            else:
                array_elements = [
                    Input(f'{self.name}_{n}', base_type, idx=self.idx).make_single_type() for n in range(array_length)
                ]
            return KEVM.abi_array(
                array_elements[0],
                intToken(array_length),
                array_elements,
            )

        else:
            return KEVM.abi_type(self.type, KVariable(self.arg_name))

    def to_abi(self) -> KApply:
        if self.type == 'tuple':
            return Input._make_tuple_type(self.components)
        else:
            return self.make_single_type()

    def flattened(self) -> list[Input]:
        components = []

        if self.type.endswith('[]'):
            if self.array_lengths is None:
                raise ValueError(f'Array length bounds missing for {self.name}')

            base_type = self.type.rstrip('[]')
            if base_type == 'tuple':
                components = [
                    Input(
                        f'{_c.name}_{i}',
                        _c.type,
                        _c.components,
                        _c.idx,
                        _c.array_lengths,
                        _c.dynamic_type_length,
                    )
                    for i in range(self.array_lengths[0])
                    for _c in self.components
                ]
            else:
                components = [Input(f'{self.name}_{i}', base_type, idx=self.idx) for i in range(self.array_lengths[0])]
        elif self.type == 'tuple':
            components = list(self.components)
        else:
            return [self]

        nest = [comp.flattened() for comp in components]
        return [fcomp for fncomp in nest for fcomp in fncomp]


def inputs_from_abi(abi_inputs: Iterable[dict], natspec_lengths: dict | None) -> list[Input]:
    def count_components(input: Input) -> int:
        if len(input.components) > 0:
            return sum(count_components(component) for component in input.components)
        else:
            return 1

    inputs = []
    index = 0
    for input in abi_inputs:
        cur_input = Input.from_dict(input, index, natspec_lengths)
        inputs.append(cur_input)
        index += count_components(cur_input)
    return inputs


def process_length_equals(input_dict: dict, lengths: dict) -> tuple[tuple[int, ...] | None, int | None]:
    """
    Read from NatSpec comments the maximum length bound of an array, dynamic type, array of dynamic type, or nested arrays.

    In case of arrays and nested arrays, the bound values are stored in an immutable list.
    In case of dynamic types such as `string` and `bytes` the length bound is stored in its own variable.
    As a convention, the length of a one-dimensional array (`bytes[]`), the length is represented as a single integer.
    For a nested array, the length is represented as a sequence of whitespace-separated integers, e.g., `10 10 10`.
    If an array length is missing, the default value will be `2` to avoid generating symbolic variables.
    The dynamic type length is optional, ommiting it may cause branchings in symbolic execution.
    """
    _name: str = input_dict['name']
    _type: str = input_dict['type']
    dynamic_type_length: int | None
    input_array_lengths: tuple[int, ...] | None
    array_lengths: list[int] = []

    array_dimensions = _type.count('[]')
    if array_dimensions:
        all_array_lengths = lengths.get('kontrol-array-length-equals')
        this_array_lengths = all_array_lengths.get(_name) if all_array_lengths is not None else None
        if this_array_lengths is not None:
            array_lengths = [this_array_lengths] if isinstance(this_array_lengths, int) else this_array_lengths
        else:
            array_lengths = [2] * array_dimensions

        # If an insufficient number of lengths was provided, add default length `2` for every missing dimension
        if len(array_lengths) < array_dimensions:
            array_lengths.extend([2] * (array_dimensions - len(array_lengths)))

    input_array_lengths = tuple(array_lengths) if array_lengths else None

    all_dynamic_type_lengths = lengths.get('kontrol-bytes-length-equals')
    dynamic_type_length = (
        all_dynamic_type_lengths.get(_name)
        if _type.startswith(('bytes', 'string')) and all_dynamic_type_lengths is not None
        else None
    )
    return (input_array_lengths, dynamic_type_length)


def parse_devdoc(tag: str, devdoc: dict | None) -> dict:
    """
    Parse developer documentation (devdoc) to extract specific information based on a given tag.

    Example:
        If devdoc contains { '@custom:kontrol-array-length-equals': 'content: 10,_withdrawalProof: 10 10,_l2OutputIndex 4,'},
        and the function is called with tag='@custom:kontrol-array-length-equals', it would return:
        { 'content': 10, '_withdrawalProof': [10, 10], '_l2OutputIndex': 4 }
    """

    if devdoc is None or tag not in devdoc:
        return {}

    natspecs = {}
    natspec_values = devdoc[tag]

    for part in natspec_values.split(','):
        # Trim whitespace and skip if empty
        part = part.strip()
        if not part:
            continue

        # Split each part into variable and length
        try:
            key, value_str = part.split(':')
            key = key.strip()
            values = value_str.split()
            natspecs[key] = [int(value.strip()) for value in values] if len(values) > 1 else int(values[0].strip())
        except ValueError:
            _LOGGER.warning(f'Skipping invalid format {part} in {tag}')
    return natspecs


@dataclass
class StorageField:
    label: str
    data_type: str
    slot: int
    offset: int

    def __init__(self, label: str, data_type: str, slot: int, offset: int) -> None:
        self.label = label
        self.data_type = data_type
        self.slot = slot
        self.offset = offset


@dataclass
class Contract:
    @dataclass
    class Constructor:
        sort: KSort
        arg_names: tuple[str, ...]
        arg_types: tuple[str, ...]
        contract_name: str
        contract_digest: str
        contract_storage_digest: str
        payable: bool
        signature: str

        def __init__(
            self,
            abi: dict,
            contract_name: str,
            contract_digest: str,
            contract_storage_digest: str,
            sort: KSort,
        ) -> None:
            self.signature = 'init'
            self.arg_names = tuple([f'V{i}_{input["name"].replace("-", "_")}' for i, input in enumerate(abi['inputs'])])
            self.arg_types = tuple([input['type'] for input in abi['inputs']])
            self.contract_name = contract_name
            self.contract_digest = contract_digest
            self.contract_storage_digest = contract_storage_digest
            self.sort = sort
            # TODO: Check that we're handling all state mutability cases
            self.payable = abi['stateMutability'] == 'payable'

        @cached_property
        def is_setup(self) -> bool:
            return False

        @cached_property
        def is_test(self) -> bool:
            return False

        @cached_property
        def is_testfail(self) -> bool:
            return False

        @cached_property
        def qualified_name(self) -> str:
            return f'{self.contract_name}.init'

        def up_to_date(self, digest_file: Path) -> bool:
            if not digest_file.exists():
                return False
            digest_dict = json.loads(digest_file.read_text())
            if 'methods' not in digest_dict:
                digest_dict['methods'] = {}
                digest_file.write_text(json.dumps(digest_dict))
            if self.qualified_name not in digest_dict['methods']:
                return False
            return digest_dict['methods'][self.qualified_name]['method'] == self.digest

        def update_digest(self, digest_file: Path) -> None:
            digest_dict = {}
            if digest_file.exists():
                digest_dict = json.loads(digest_file.read_text())
            if 'methods' not in digest_dict:
                digest_dict['methods'] = {}
            digest_dict['methods'][self.qualified_name] = {'method': self.digest}
            digest_file.write_text(json.dumps(digest_dict))

            _LOGGER.info(f'Updated method {self.qualified_name} in digest file: {digest_file}')

        @cached_property
        def digest(self) -> str:
            contract_digest = self.contract_digest
            return hash_str(f'{self.contract_storage_digest}{contract_digest}')

    @dataclass
    class Method:
        name: str
        id: int
        sort: KSort
        inputs: tuple[Input, ...]
        contract_name: str
        contract_name_with_path: str
        contract_digest: str
        contract_storage_digest: str
        payable: bool
        signature: str
        ast: dict | None
        natspec_values: dict | None
        function_calls: tuple[str, ...] | None

        def __init__(
            self,
            msig: str,
            id: int,
            abi: dict,
            ast: dict | None,
            contract_name_with_path: str,
            contract_digest: str,
            contract_storage_digest: str,
            sort: KSort,
            devdoc: dict | None,
            function_calls: Iterable[str] | None,
        ) -> None:
            self.signature = msig
            self.name = abi['name']
            self.id = id
            self.contract_name_with_path = contract_name_with_path
            self.contract_name = contract_name_with_path.split('%')[-1]
            self.contract_digest = contract_digest
            self.contract_storage_digest = contract_storage_digest
            self.sort = sort
            # TODO: Check that we're handling all state mutability cases
            self.payable = abi['stateMutability'] == 'payable'
            self.ast = ast
            natspec_tags = ['custom:kontrol-array-length-equals', 'custom:kontrol-bytes-length-equals']
            self.natspec_values = {tag.split(':')[1]: parse_devdoc(tag, devdoc) for tag in natspec_tags}
            self.inputs = tuple(inputs_from_abi(abi['inputs'], self.natspec_values))
            self.function_calls = tuple(function_calls) if function_calls is not None else None

        @property
        def klabel(self) -> KLabel:
            args_list = '_'.join(self.arg_types)
            return KLabel(f'method_{self.contract_name_with_path}_{self.unique_name}_{args_list}')

        @property
        def unique_klabel(self) -> KLabel:
            args_list = '_'.join(self.arg_types)
            return KLabel(f'method_{self.contract_name_with_path}_{self.unique_name}_{args_list}')

        @property
        def unique_name(self) -> str:
            return f'{Contract.escaped(self.name, "S2K")}'

        @cached_property
        def qualified_name(self) -> str:
            return f'{self.contract_name_with_path}.{self.signature}'

        @property
        def selector_alias_rule(self) -> KRule:
            return KRule(KRewrite(KEVM.abi_selector(self.signature), intToken(self.id)))

        @cached_property
        def is_setup(self) -> bool:
            return self.name == 'setUp'

        @cached_property
        def is_test(self) -> bool:
            proof_prefixes = ['test', 'check', 'prove']
            return any(self.name.startswith(prefix) for prefix in proof_prefixes)

        @cached_property
        def is_testfail(self) -> bool:
            proof_prefixes = ['testFail', 'checkFail', 'proveFail']
            return any(self.name.startswith(prefix) for prefix in proof_prefixes)

        @cached_property
        def flat_inputs(self) -> tuple[Input, ...]:
            return tuple(input for sub_inputs in self.inputs for input in sub_inputs.flattened())

        @cached_property
        def arg_names(self) -> tuple[str, ...]:
            arg_names: list[str] = []
            for input in self.inputs:
                if input.type.endswith('[]') and not input.type.startswith('tuple'):
                    if input.array_lengths is None:
                        raise ValueError(f'Array length bounds missing for {input.name}')
                    length = input.array_lengths[0]
                    arg_names.extend(f'{input.arg_name}_{i}' for i in range(length))
                else:
                    arg_names.extend([sub_input.arg_name for sub_input in input.flattened()])
            return tuple(arg_names)

        @cached_property
        def arg_types(self) -> tuple[str, ...]:
            arg_types: list[str] = []
            for input in self.inputs:
                if input.type.endswith('[]'):
                    if input.array_lengths is None:
                        raise ValueError(f'Array length bounds missing for {input.name}')
                    length = input.array_lengths[0]
                    base_type = input.type.split('[')[0]
                    if base_type == 'tuple':
                        arg_types.extend([sub_input.type for sub_input in input.flattened()])
                    else:
                        arg_types.extend([base_type] * length)

                else:
                    arg_types.extend([sub_input.type for sub_input in input.flattened()])
            return tuple(arg_types)

        def up_to_date(self, digest_file: Path) -> bool:
            if not digest_file.exists():
                return False
            digest_dict = json.loads(digest_file.read_text())
            if 'methods' not in digest_dict:
                digest_dict['methods'] = {}
                digest_file.write_text(json.dumps(digest_dict, indent=4))
            if self.qualified_name not in digest_dict['methods']:
                return False
            return digest_dict['methods'][self.qualified_name]['method'] == self.digest

        def contract_up_to_date(self, digest_file: Path) -> bool:
            if not digest_file.exists():
                return False
            digest_dict = json.loads(digest_file.read_text())
            if 'methods' not in digest_dict:
                digest_dict['methods'] = {}
                digest_file.write_text(json.dumps(digest_dict, indent=4))
            if self.qualified_name not in digest_dict['methods']:
                return False
            return digest_dict['methods'][self.qualified_name]['contract'] == self.contract_digest

        def update_digest(self, digest_file: Path) -> None:
            digest_dict = {}
            if digest_file.exists():
                digest_dict = json.loads(digest_file.read_text())
            if 'methods' not in digest_dict:
                digest_dict['methods'] = {}
            digest_dict['methods'][self.qualified_name] = {'method': self.digest, 'contract': self.contract_digest}
            digest_file.write_text(json.dumps(digest_dict, indent=4))

            _LOGGER.info(f'Updated method {self.qualified_name} in digest file: {digest_file}')

        @cached_property
        def digest(self) -> str:
            ast = json.dumps(self.ast, sort_keys=True) if self.ast is not None else {}
            contract_digest = self.contract_digest if not self.is_setup else {}
            return hash_str(f'{self.signature}{ast}{self.contract_storage_digest}{contract_digest}')

        @property
        def production(self) -> KProduction:
            items_before: list[KProductionItem] = [KTerminal(self.unique_name), KTerminal('(')]

            items_args: list[KProductionItem] = []
            for i, input_type in enumerate(self.arg_types):
                if i > 0:
                    items_args += [KTerminal(',')]
                items_args += [KNonTerminal(_evm_base_sort(input_type)), KTerminal(':'), KTerminal(input_type)]

            items_after: list[KProductionItem] = [KTerminal(')')]
            return KProduction(
                self.sort,
                items_before + items_args + items_after,
                klabel=self.unique_klabel,
                att=KAtt(entries=[Atts.SYMBOL('')]),
            )

        def rule(self, contract: KInner, application_label: KLabel, contract_name: str) -> KRule | None:
            prod_klabel = self.unique_klabel
            arg_vars = [KVariable(name) for name in self.arg_names]
            args: list[KInner] = []
            conjuncts: list[KInner] = []
            for input in self.inputs:
                abi_type = input.to_abi()
                args.append(abi_type)
                rps = []
                if input.type.startswith('tuple'):
                    components = input.components

                    if input.type.endswith('[]'):
                        if input.array_lengths is None:
                            raise ValueError(f'Array length bounds missing for {input.name}')

                        tuple_array_components = [
                            Input(
                                f'{_c.name}_{i}',
                                _c.type,
                                _c.components,
                                _c.idx,
                                _c.array_lengths,
                                _c.dynamic_type_length,
                            )
                            for i in range(input.array_lengths[0])
                            for _c in components
                        ]
                        components = tuple(tuple_array_components)

                    for sub_input in components:
                        _abi_type = sub_input.to_abi()
                        rps.extend(_range_predicates(_abi_type, sub_input.dynamic_type_length))
                else:
                    rps = _range_predicates(abi_type, input.dynamic_type_length)
                for rp in rps:
                    if rp is None:
                        _LOGGER.info(
                            f'Unsupported ABI type for method {contract_name}.{prod_klabel.name}, will not generate calldata sugar: {input.type}'
                        )
                        return None
                    conjuncts.append(rp)
            lhs = KApply(application_label, [contract, KApply(prod_klabel, arg_vars)])
            rhs = KEVM.abi_calldata(self.name, args)
            ensures = andBool(conjuncts)
            return KRule(KRewrite(lhs, rhs), ensures=ensures)

        @cached_property
        def callvalue_cell(self) -> KInner:
            return (
                intToken(0)
                if not self.payable
                else abstract_term_safely(KVariable('_###CALLVALUE###_'), base_name='CALLVALUE')
            )

        def calldata_cell(self, contract: Contract) -> KInner:
            return KApply(contract.klabel_method, [KApply(contract.klabel), self.application])

        @cached_property
        def application(self) -> KInner:
            klabel = self.klabel
            assert klabel is not None
            args = [
                abstract_term_safely(KVariable('_###SOLIDITY_ARG_VAR###_'), base_name=f'V{name}')
                for name in self.arg_names
            ]
            return klabel(args)

    _name: str
    contract_json: dict
    contract_id: int
    contract_path: str
    deployed_bytecode: str
    bytecode: str
    raw_sourcemap: str | None
    methods: tuple[Method, ...]
    fields: tuple[StorageField, ...]
    constructor: Constructor | None
    PREFIX_CODE: Final = 'Z'

    def __init__(self, contract_name: str, contract_json: dict, foundry: bool = False) -> None:
        self._name = contract_name
        self.contract_json = contract_json

        self.contract_id = self.contract_json['id']
        try:
            self.contract_path = self.contract_json['ast']['absolutePath']
        except KeyError:
            raise ValueError(
                "Must have 'ast' field in solc output. Make sure `ast = true` is present in foundry.toml"
            ) from None

        evm = self.contract_json['evm'] if not foundry else self.contract_json

        deployed_bytecode = evm['deployedBytecode']
        self.deployed_bytecode = deployed_bytecode['object'].replace('0x', '')
        self.raw_sourcemap = deployed_bytecode['sourceMap'] if 'sourceMap' in deployed_bytecode else None

        bytecode = evm['bytecode']
        self.bytecode = bytecode['object'].replace('0x', '')
        self.constructor = None

        contract_ast_nodes = [
            node
            for node in self.contract_json['ast']['nodes']
            if node['nodeType'] == 'ContractDefinition' and node['name'] == self._name
        ]
        contract_ast = single(contract_ast_nodes) if len(contract_ast_nodes) > 0 else {'nodes': []}
        function_asts = {
            node['functionSelector']: node
            for node in contract_ast['nodes']
            if node['nodeType'] == 'FunctionDefinition' and 'functionSelector' in node
        }

        _methods = []
        metadata = self.contract_json.get('metadata', {})
        devdoc = metadata.get('output', {}).get('devdoc', {}).get('methods', {})

        for method in contract_json['abi']:
            if method['type'] == 'function':
                msig = method_sig_from_abi(method)
                method_selector: str = str(evm['methodIdentifiers'][msig])
                mid = int(method_selector, 16)
                method_ast = function_asts[method_selector] if method_selector in function_asts else None
                method_devdoc = devdoc.get(msig)
                method_calls = find_function_calls(method_ast)
                _m = Contract.Method(
                    msig,
                    mid,
                    method,
                    method_ast,
                    self.name_with_path,
                    self.digest,
                    self.storage_digest,
                    self.sort_method,
                    method_devdoc,
                    method_calls,
                )
                _methods.append(_m)
            if method['type'] == 'constructor':
                _c = Contract.Constructor(method, self._name, self.digest, self.storage_digest, self.sort_method)
                self.constructor = _c

        self.methods = tuple(sorted(_methods, key=(lambda method: method.signature)))

        if self.constructor is None:
            empty_constructor = {'inputs': [], 'stateMutability': 'nonpayable', 'type': 'constructor'}
            _c = Contract.Constructor(empty_constructor, self._name, self.digest, self.storage_digest, self.sort_method)
            self.constructor = _c

        self.fields = self.process_storage_fields()
        # _PPRINT.pprint(contract_name)
        # _PPRINT.pprint(self.fields)

    @cached_property
    def name_with_path(self) -> str:
        contract_path_without_filename = '%'.join(self.contract_path.split('/')[0:-1])
        return self._name if contract_path_without_filename == '' else contract_path_without_filename + '%' + self._name

    @cached_property
    def digest(self) -> str:
        return hash_str(f'{self.name_with_path} - {json.dumps(self.contract_json, sort_keys=True)}')

    @cached_property
    def storage_digest(self) -> str:
        storage_layout = self.contract_json.get('storageLayout') or {}
        return hash_str(f'{self.name_with_path} - {json.dumps(storage_layout, sort_keys=True)}')

    @cached_property
    def srcmap(self) -> dict[int, tuple[int, int, int, str, int]]:
        _srcmap = {}

        if len(self.deployed_bytecode) > 0 and self.raw_sourcemap is not None:
            instr_to_pc = {}
            pc = 0
            instr = 0
            bs = [int(self.deployed_bytecode[i : i + 2], 16) for i in range(0, len(self.deployed_bytecode), 2)]
            while pc < len(bs):
                b = bs[pc]
                instr_to_pc[instr] = pc
                if 0x60 <= b and b < 0x7F:
                    push_width = b - 0x5F
                    pc = pc + push_width
                pc += 1
                instr += 1

            instrs_srcmap = self.raw_sourcemap.split(';')

            s, l, f, j, m = (0, 0, 0, '', 0)
            for i, instr_srcmap in enumerate(instrs_srcmap):
                fields = instr_srcmap.split(':')
                if len(fields) > 0 and fields[0] != '':
                    s = int(fields[0])
                if len(fields) > 1 and fields[1] != '':
                    l = int(fields[1])
                if len(fields) > 2 and fields[2] != '':
                    f = int(fields[2])
                if len(fields) > 3 and fields[3] != '':
                    j = fields[3]
                if len(fields) > 4 and fields[4] != '':
                    m = int(fields[4])
                _srcmap[i] = (s, l, f, j, m)

        return _srcmap

    @staticmethod
    def contract_to_module_name(c: str) -> str:
        return Contract.escaped(c, 'S2K') + '-CONTRACT'

    @staticmethod
    def contract_to_verification_module_name(c: str) -> str:
        return Contract.escaped(c, 'S2K') + '-VERIFICATION'

    @staticmethod
    def test_to_claim_name(t: str) -> str:
        return t.replace('_', '-')

    @staticmethod
    def escaped_chars() -> list[str]:
        return [Contract.PREFIX_CODE, '_', '$', '.', '-', '%', '@']

    @staticmethod
    def escape_char(char: str) -> str:
        match char:
            case Contract.PREFIX_CODE:
                as_ecaped = Contract.PREFIX_CODE
            case '_':
                as_ecaped = 'Und'
            case '$':
                as_ecaped = 'Dlr'
            case '.':
                as_ecaped = 'Dot'
            case '-':
                as_ecaped = 'Sub'
            case '%':
                as_ecaped = 'Mod'
            case '@':
                as_ecaped = 'At'
            case _:
                as_ecaped = hex(ord(char)).removeprefix('0x')
        return f'{Contract.PREFIX_CODE}{as_ecaped}'

    @staticmethod
    def unescape_seq(seq: str) -> tuple[str, int]:
        if seq.startswith(Contract.PREFIX_CODE + Contract.PREFIX_CODE):
            return Contract.PREFIX_CODE, 1
        elif seq.startswith('Und'):
            return '_', 3
        elif seq.startswith('Dlr'):
            return '$', 3
        elif seq.startswith('Dot'):
            return '.', 3
        elif seq.startswith('Sub'):
            return '-', 3
        elif seq.startswith('Mod'):
            return '%', 3
        elif seq.startswith('At'):
            return '@', 2
        else:
            return chr(int(seq, base=16)), 4

    @staticmethod
    def escaped(name: str, prefix: str) -> str:
        """
        escape all the chars that would cause issues once kompiling and add a prefix to mark it as "escaped"
        """
        escaped = [Contract.escape_char(char) if char in Contract.escaped_chars() else char for char in iter(name)]
        return prefix + ''.join(escaped)

    @staticmethod
    def unescaped(name: str, prefix: str = '') -> str:
        if not name.startswith(prefix):
            raise RuntimeError(f'name {name} should start with {prefix}')
        unescaped = name.removeprefix(prefix)
        res = []
        skipped = 0
        i = 0
        while i + skipped < len(unescaped[:-1]):
            j = i + skipped
            char = unescaped[j]
            next_char = unescaped[j + 1]
            if char == Contract.PREFIX_CODE:
                unesc, to_skip = Contract.unescape_seq(unescaped[(j + 1) : (j + 4)])
                res.append(unesc)
                for _ in range(to_skip):
                    skipped += 1
            else:
                res.append(char)
            # write last char
            if j + 2 == len(unescaped):
                res.append(next_char)
            i += 1
        return ''.join(res)

    @property
    def sort(self) -> KSort:
        return KSort(f'{Contract.escaped(self.name_with_path, "S2K")}Contract')

    @property
    def sort_field(self) -> KSort:
        return KSort(f'{Contract.escaped(self.name_with_path, "S2K")}Field')

    @property
    def sort_method(self) -> KSort:
        return KSort(f'{Contract.escaped(self.name_with_path, "S2K")}Method')

    @property
    def klabel(self) -> KLabel:
        return KLabel(f'contract_{self.name_with_path}')

    @property
    def klabel_method(self) -> KLabel:
        return KLabel(f'method_{self.name_with_path}')

    @property
    def klabel_field(self) -> KLabel:
        return KLabel(f'field_{self.name_with_path}')

    @property
    def subsort(self) -> KProduction:
        return KProduction(KSort('Contract'), [KNonTerminal(self.sort)])

    @property
    def subsort_field(self) -> KProduction:
        return KProduction(KSort('Field'), [KNonTerminal(self.sort_field)])

    @property
    def production(self) -> KProduction:
        return KProduction(
            self.sort,
            [KTerminal(Contract.escaped(self.name_with_path, 'S2K'))],
            klabel=self.klabel,
            att=KAtt([Atts.SYMBOL('')]),
        )

    @property
    def macro_bin_runtime(self) -> KRule:
        if self.has_unlinked():
            raise ValueError(
                f'Some library placeholders have been found in contract {self.name_with_path}. Please link the library(ies) first. Ref: https://docs.soliditylang.org/en/v0.8.20/using-the-compiler.html#library-linking'
            )
        return KRule(
            KRewrite(
                KEVM.bin_runtime(KApply(self.klabel)), KEVM.parse_bytestack(stringToken('0x' + self.deployed_bytecode))
            )
        )

    @property
    def macro_init_bytecode(self) -> KRule:
        if self.has_unlinked():
            raise ValueError(
                f'Some library placeholders have been found in contract {self.name_with_path}. Please link the library(ies) first. Ref: https://docs.soliditylang.org/en/v0.8.20/using-the-compiler.html#library-linking'
            )
        return KRule(
            KRewrite(KEVM.init_bytecode(KApply(self.klabel)), KEVM.parse_bytestack(stringToken('0x' + self.bytecode)))
        )

    def has_unlinked(self) -> bool:
        return 0 <= self.deployed_bytecode.find('__')

    @property
    def method_sentences(self) -> list[KSentence]:
        method_application_production: KSentence = KProduction(
            KSort('Bytes'),
            [KNonTerminal(self.sort), KTerminal('.'), KNonTerminal(self.sort_method)],
            klabel=self.klabel_method,
            att=KAtt(entries=[Atts.FUNCTION(None), Atts.SYMBOL('')]),
        )
        res: list[KSentence] = [method_application_production]
        res.extend(method.production for method in self.methods)
        method_rules = (
            method.rule(KApply(self.klabel), self.klabel_method, self.name_with_path) for method in self.methods
        )
        res.extend(rule for rule in method_rules if rule)
        res.extend(method.selector_alias_rule for method in self.methods)
        return res if len(res) > 1 else []

    @property
    def sentences(self) -> list[KSentence]:
        return [self.subsort, self.production, self.macro_bin_runtime, self.macro_init_bytecode] + self.method_sentences

    @property
    def method_by_name(self) -> dict[str, Contract.Method]:
        return {method.name: method for method in self.methods}

    @property
    def method_by_sig(self) -> dict[str, Contract.Method]:
        return {method.signature: method for method in self.methods}

    def process_storage_fields(self) -> tuple[StorageField, ...]:
        fields_list = []
        storage_layout = self.contract_json.get('storageLayout', {})
        storage = storage_layout.get('storage', [])
        types = storage_layout.get('types', {})

        for field in storage:
            try:
                label = field['label']
                slot = int(field['slot'])
                offset = int(field['offset'])
                data_type = field['type']
                type_info = types.get(data_type, {})
                data_type_label = type_info.get('label', data_type)

                storage_field = StorageField(label=label, data_type=data_type_label, slot=slot, offset=offset)
                fields_list.append(storage_field)

            except (KeyError, ValueError) as e:
                _LOGGER.error(f'Error processing field {field} in contract {self._name}: {e}')

        return tuple(fields_list)


def solc_compile(contract_file: Path) -> dict[str, Any]:
    # TODO: add check to kevm:
    # solc version should be >=0.8.0 due to:
    # https://github.com/ethereum/solidity/issues/10276

    args = {
        'language': 'Solidity',
        'sources': {
            contract_file.name: {
                'urls': [
                    str(contract_file),
                ],
            },
        },
        'settings': {
            'outputSelection': {
                '*': {
                    '*': [
                        'abi',
                        'storageLayout',
                        'evm.methodIdentifiers',
                        'evm.deployedBytecode.object',
                        'evm.deployedBytecode.sourceMap',
                        'evm.bytecode.object',
                        'evm.bytecode.sourceMap',
                    ],
                    '': ['ast'],
                },
            },
        },
    }

    try:
        process_res = run_process(['solc', '--standard-json'], logger=_LOGGER, input=json.dumps(args))
    except CalledProcessError as err:
        raise RuntimeError('solc error', err.stdout, err.stderr) from err
    result = json.loads(process_res.stdout)
    if 'errors' in result:
        failed = False
        for error in result['errors']:
            if error['severity'] == 'error':
                _LOGGER.error(f'solc error:\n{error["formattedMessage"]}')
                failed = True
            elif error['severity'] == 'warning':
                _LOGGER.warning(f'solc warning:\n{error["formattedMessage"]}')
            else:
                _LOGGER.warning(
                    f'Unknown solc error severity level {error["severity"]}:\n{json.dumps(error, indent=2)}'
                )
        if failed:
            raise ValueError('Compilation failed.')
    return result


def contract_to_main_module(contract: Contract, empty_config: KInner, imports: Iterable[str] = ()) -> KFlatModule:
    module_name = Contract.contract_to_module_name(contract.name_with_path)
    return KFlatModule(module_name, contract.sentences, [KImport(i) for i in list(imports)])


def contract_to_verification_module(contract: Contract, empty_config: KInner, imports: Iterable[str]) -> KFlatModule:
    main_module_name = Contract.contract_to_module_name(contract.name_with_path)
    verification_module_name = Contract.contract_to_verification_module_name(contract.name_with_path)
    return KFlatModule(verification_module_name, [], [KImport(main_module_name)] + [KImport(i) for i in list(imports)])


# Helpers


def _evm_base_sort(type_label: str) -> KSort:
    if _evm_base_sort_int(type_label):
        return KSort('Int')

    if type_label == 'bytes':
        return KSort('Bytes')

    if type_label == 'string':
        return KSort('String')

    _LOGGER.info(f'Using generic sort K for type: {type_label}')
    return KSort('K')


def _evm_base_sort_int(type_label: str) -> bool:
    success = False

    # Check address and bool
    if type_label in {'address', 'bool'}:
        success = True

    # Check bytes
    if type_label.startswith('bytes') and len(type_label) > 5 and not type_label.endswith(']'):
        width = int(type_label[5:])
        if not (0 < width <= 32):
            raise ValueError(f'Unsupported evm base sort type: {type_label}')
        else:
            success = True

    # Check ints
    if type_label.startswith('int') and not type_label.endswith(']'):
        width = int(type_label[3:])
        if not (0 < width and width <= 256 and width % 8 == 0):
            raise ValueError(f'Unsupported evm base sort type: {type_label}')
        else:
            success = True

    # Check uints
    if type_label.startswith('uint') and not type_label.endswith(']'):
        width = int(type_label[4:])
        if not (0 < width and width <= 256 and width % 8 == 0):
            raise ValueError(f'Unsupported evm base sort type: {type_label}')
        else:
            success = True

    return success


def _range_predicates(abi: KApply, dynamic_type_length: int | None = None) -> list[KInner | None]:
    rp: list[KInner | None] = []
    if abi.label.name == 'abi_type_tuple':
        if type(abi.args[0]) is KApply:
            rp += _range_collection_predicates(abi.args[0], dynamic_type_length)
    elif abi.label.name == 'abi_type_array':
        # array elements:
        if type(abi.args[2]) is KApply:
            rp += _range_collection_predicates(abi.args[2], dynamic_type_length)
    else:
        type_label = abi.label.name.removeprefix('abi_type_')
        rp.append(_range_predicate(single(abi.args), type_label, dynamic_type_length))
    return rp


def _range_collection_predicates(abi: KApply, dynamic_type_length: int | None = None) -> list[KInner | None]:
    rp: list[KInner | None] = []
    if abi.label.name == 'typedArgs':
        if type(abi.args[0]) is KApply:
            rp += _range_predicates(abi.args[0], dynamic_type_length)
        if type(abi.args[1]) is KApply:
            rp += _range_collection_predicates(abi.args[1], dynamic_type_length)
    elif abi.label.name == '.List{"typedArgs"}':
        return rp
    else:
        raise AssertionError('No list of typed args found')
    return rp


def _range_predicate(term: KInner, type_label: str, dynamic_type_length: int | None = None) -> KInner | None:
    match type_label:
        case 'address':
            return KEVM.range_address(term)
        case 'bool':
            return KEVM.range_bool(term)
        case 'bytes':
            #  the compiler-inserted check asserts that lengthBytes(B) <= maxUint64
            return (
                eqInt(KEVM.size_bytes(term), intToken(dynamic_type_length))
                if dynamic_type_length
                else KEVM.range_uint(64, KEVM.size_bytes(term))
            )
        case 'string':
            return eqInt(KEVM.size_bytes(term), intToken(dynamic_type_length)) if dynamic_type_length else TRUE

    predicate_functions = [
        _range_predicate_uint,
        _range_predicate_int,
        _range_predicate_bytes,
    ]

    for f in predicate_functions:
        (success, result) = f(term, type_label)
        if success:
            return result

    _LOGGER.info(f'Unknown range predicate for type: {type_label}')
    return None


def _range_predicate_uint(term: KInner, type_label: str) -> tuple[bool, KApply | None]:
    if type_label.startswith('uint') and not type_label.endswith(']'):
        if type_label == 'uint':
            width = 256
        else:
            width = int(type_label[4:])
        if not (0 < width <= 256 and width % 8 == 0):
            raise ValueError(f'Unsupported range predicate uint<M> type: {type_label}')
        return (True, KEVM.range_uint(width, term))
    else:
        return (False, None)


def _range_predicate_int(term: KInner, type_label: str) -> tuple[bool, KApply | None]:
    if type_label.startswith('int') and not type_label.endswith(']'):
        if type_label == 'int':
            width = 256
        else:
            width = int(type_label[3:])
        if not (0 < width and width <= 256 and width % 8 == 0):
            raise ValueError(f'Unsupported range predicate int<M> type: {type_label}')
        return (True, KEVM.range_sint(width, term))
    else:
        return (False, None)


def _range_predicate_bytes(term: KInner, type_label: str) -> tuple[bool, KApply | None]:
    if type_label.startswith('bytes') and not type_label.endswith(']'):
        str_width = type_label[5:]
        if str_width != '':
            width = int(str_width)
            if not (0 < width and width <= 32):
                raise ValueError(f'Unsupported range predicate bytes<M> type: {type_label}')
            return (True, KEVM.range_bytes(intToken(width), term))
    return (False, None)


def method_sig_from_abi(method_json: dict) -> str:
    def unparse_input(input_json: dict) -> str:
        is_array = False
        is_sized = False
        array_size = 0
        base_type = input_json['type']
        if re.match(r'.+\[.*\]', base_type):
            is_array = True
            array_size_str = base_type.split('[')[1][:-1]
            if array_size_str != '':
                is_sized = True
                array_size = int(array_size_str)
            base_type = base_type.split('[')[0]
        if base_type == 'tuple':
            input_type = '('
            for i, component in enumerate(input_json['components']):
                if i != 0:
                    input_type += ','
                input_type += unparse_input(component)
            input_type += ')'
            if is_array and not (is_sized):
                input_type += '[]'
            elif is_array and is_sized:
                input_type += f'[{array_size}]'
            return input_type
        else:
            return input_json['type']

    method_name = method_json['name']
    method_args = ''
    for i, _input in enumerate(method_json['inputs']):
        if i != 0:
            method_args += ','
        method_args += unparse_input(_input)
    return f'{method_name}({method_args})'


def hex_string_to_int(hex: str) -> int:
    if hex.startswith('0x'):
        return int(hex, 16)
    else:
        raise ValueError('Invalid hex format')


def find_function_calls(node: dict) -> list[str]:
    """Recursive function that takes a method AST and returns all the functions that are called in the given method.

    :param node: AST of a Solidity Method
    :type node: dict
    :return: A list of unique function signatures that are called inside the provided method AST.
    :rtype: list[str]

    Functions that belong to contracts such as `Vm` and `KontrolCheatsBase` are ignored.
    Functions like `abi.encodePacked` that do not belong to a Contract are assigned to a `UnknownContractType` and are ignored.
    """
    function_calls: list[str] = []

    def _find_function_calls(node: dict) -> None:
        if not node:
            return

        if node.get('nodeType') == 'FunctionCall':
            expression = node.get('expression', {})
            if expression.get('nodeType') == 'MemberAccess':
                contract_type_string = expression['expression']['typeDescriptions'].get('typeString', '')
                contract_type = (
                    contract_type_string.split()[-1] if 'contract' in contract_type_string else 'UnknownContractType'
                )

                function_name = expression.get('memberName')
                arg_types = expression['typeDescriptions'].get('typeString')
                args = arg_types.split()[1] if arg_types is not None else '()'

                if contract_type not in ['KontrolCheatsBase', 'Vm', 'UnknownContractType']:
                    value = f'{contract_type}.{function_name}{args}'
                    # Check if value is not already in the list
                    if value not in function_calls:
                        function_calls.append(value)

        for _key, value in node.items():
            if isinstance(value, dict):
                _find_function_calls(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _find_function_calls(item)

    _find_function_calls(node)
    return function_calls
