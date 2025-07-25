from __future__ import annotations

import ast
import json
import logging
import re
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, NamedTuple

from eth_abi import decode
from kevm_pyk.kevm import KEVM
from pyk.kast.inner import KApply, KLabel, KSort, KToken, KVariable
from pyk.kast.prelude.kbool import TRUE
from pyk.kast.prelude.kint import eqInt, intToken, ltInt
from pyk.utils import hash_str, single

from .utils import _read_digest_file

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path
    from typing import Final

    from pyk.kast import KInner


_LOGGER: Final = logging.getLogger(__name__)


@dataclass(frozen=True)
class Input:
    name: str
    type: str
    components: tuple[Input, ...] = ()
    idx: int = 0
    internal_type: str | None = None
    array_lengths: tuple[int, ...] | None = None
    dynamic_type_length: int | None = None

    @cached_property
    def arg_name(self) -> str:
        prefix = f'KV{self.idx}_' if self.name and self.name[0].isalpha() else f'KV{self.idx}'
        return f'{prefix}{self.name}'

    @staticmethod
    def from_dict(input: dict, idx: int = 0, natspec_lengths: dict | None = None) -> Input:
        """
        Creates an Input instance from a dictionary.

        If the optional devdocs is provided, it is used for calculating array and dynamic type lengths.
        For tuples, the function handles nested 'components' recursively.
        """
        name = input.get('name')
        type = input.get('type')
        internal_type = input.get('internalType')
        if name is None or type is None:
            raise ValueError("ABI dictionary must contain 'name' and 'type' keys.", input)
        array_lengths, dynamic_type_length = (
            process_length_equals(input, natspec_lengths) if natspec_lengths is not None else (None, None)
        )
        if input.get('components') is not None:
            return Input(
                name,
                type,
                internal_type=internal_type,
                components=tuple(Input._unwrap_components(input['components'], idx, natspec_lengths)),
                idx=idx,
                array_lengths=array_lengths,
                dynamic_type_length=dynamic_type_length,
            )
        else:
            return Input(
                name,
                type,
                internal_type=internal_type,
                idx=idx,
                array_lengths=array_lengths,
                dynamic_type_length=dynamic_type_length,
            )

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
                    _c.internal_type,
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
                    internal_type=component['internalType'],
                    components=tuple(Input._unwrap_components(component.get('components', []), idx, natspec_lengths)),
                    idx=idx,
                    array_lengths=lengths[0],
                    dynamic_type_length=lengths[1],
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

    @staticmethod
    def process_tuple_array(input: Input) -> list[Input]:
        """
        Processes an input tuple array, appending `_index` to the names of components
        and recursively handling nested tuples.
        """
        processed_components = []

        if input.array_lengths is None:
            raise ValueError(f'Array length bounds missing for {input.name}')

        for i in range(input.array_lengths[0]):
            for _c in input.components:
                if _c.type == 'tuple':
                    # Recursively process nested tuple components
                    sub_components = tuple(Input.add_index_to_components(_c.components, i))
                else:
                    sub_components = _c.components

                processed_component = Input(
                    f'{_c.name}_{i}',
                    _c.type,
                    sub_components,
                    _c.idx,
                    array_lengths=_c.array_lengths,
                    dynamic_type_length=_c.dynamic_type_length,
                )
                processed_components.append(processed_component)

        return processed_components

    @staticmethod
    def add_index_to_components(components: tuple[Input, ...], index: int) -> list[Input]:
        updated_components = []
        for component in components:
            if component.type == 'tuple':
                # recursively add `_{i}` index to nested tuple components
                updated_sub_components = tuple(Input.add_index_to_components(component.components, index))
            else:
                updated_sub_components = component.components
            # Update the component's name and append to the result list
            updated_component = Input(
                f'{component.name}_{index}',
                component.type,
                updated_sub_components,
                component.idx,
                array_lengths=component.array_lengths,
                dynamic_type_length=component.dynamic_type_length,
            )
            updated_components.append(updated_component)
        return updated_components

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
        components: list[Input] = []

        if self.type.endswith('[]'):
            if self.array_lengths is None:
                raise ValueError(f'Array length bounds missing for {self.name}')

            base_type = self.type.rstrip('[]')
            if base_type == 'tuple':
                components = Input.process_tuple_array(self)
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
    If an array length is missing, the default value will be `1` to avoid generating symbolic variables.
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
            array_lengths = [1] * array_dimensions

        # If an insufficient number of lengths was provided, add default length `1` for every missing dimension
        if len(array_lengths) < array_dimensions:
            array_lengths.extend([1] * (array_dimensions - len(array_lengths)))

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


class StorageField(NamedTuple):
    label: str
    data_type: str
    slot: int
    offset: int
    linked_interface: str | None


@dataclass
class Contract:
    @dataclass
    class Constructor:
        sort: KSort
        inputs: tuple[Input, ...]
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
            self.contract_name = contract_name
            self.contract_digest = contract_digest
            self.contract_storage_digest = contract_storage_digest
            # TODO: support NatSpec comments for dynamic types
            natspec_tags = ['custom:kontrol-array-length-equals', 'custom:kontrol-bytes-length-equals']
            empty_natspec_values: dict = {tag.split(':')[1]: {} for tag in natspec_tags}
            self.inputs = tuple(inputs_from_abi(abi['inputs'], empty_natspec_values))
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
            digest_dict = _read_digest_file(digest_file)
            return digest_dict.get('methods', {}).get(self.qualified_name, {}).get('method', '') == self.digest

        def update_digest(self, digest_file: Path) -> None:
            digest_dict = _read_digest_file(digest_file)
            digest_dict['methods'][self.qualified_name] = {'method': self.digest}
            digest_file.write_text(json.dumps(digest_dict, indent=4))

            _LOGGER.info(f'Updated method {self.qualified_name} in digest file: {digest_file}')

        @cached_property
        def digest(self) -> str:
            contract_digest = self.contract_digest
            return hash_str(f'{self.contract_storage_digest}{contract_digest}')

        @cached_property
        def callvalue_cell(self) -> KInner:
            return intToken(0) if not self.payable else KVariable('CALLVALUE')

        def encoded_args(self, enums: dict[str, int]) -> tuple[KInner, list[KInner]]:
            args: list[KInner] = []
            type_constraints: list[KInner] = []
            for input in self.inputs:
                abi_type = input.to_abi()
                args.append(abi_type)
                rps = []
                if input.type.startswith('tuple'):
                    components = input.components

                    if input.type.endswith('[]'):
                        if input.array_lengths is None:
                            raise ValueError(f'Array length bounds missing for {input.name}')

                    components = tuple(Input.process_tuple_array(input))
                    for sub_input in components:
                        _abi_type = sub_input.to_abi()
                        rps.extend(_range_predicates(_abi_type, sub_input.dynamic_type_length))
                else:
                    rps = _range_predicates(abi_type, input.dynamic_type_length)
                for rp in rps:
                    if rp is None:
                        raise ValueError(f'Unsupported ABI type for method for {self.contract_name}.init')
                    type_constraints.append(rp)
                if input.internal_type is not None and input.internal_type.startswith('enum '):
                    enum_name = input.internal_type.split(' ')[1]
                    if enum_name not in enums:
                        _LOGGER.warning(
                            f'Skipping adding constraint for {enum_name} because it is not tracked by kontrol. It can be automatically constrained to its possible values by adding --enum-constraints.'
                        )
                    else:
                        enum_max = enums[enum_name]
                        type_constraints.append(
                            ltInt(
                                KVariable(input.arg_name),
                                intToken(enum_max),
                            )
                        )
            encoded_args = KApply('encodeArgs', [KEVM.typed_args(args)])
            return encoded_args, type_constraints

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
        pure: bool
        view: bool
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
            self.pure = abi['stateMutability'] == 'pure'
            self.view = abi['stateMutability'] == 'view'
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
            digest_dict = _read_digest_file(digest_file)
            return digest_dict.get('methods', {}).get(self.qualified_name, {}).get('method', '') == self.digest

        def contract_up_to_date(self, digest_file: Path) -> bool:
            digest_dict = _read_digest_file(digest_file)
            return (
                digest_dict.get('methods', {}).get(self.qualified_name, {}).get('contract', '') == self.contract_digest
            )

        def update_digest(self, digest_file: Path) -> None:
            digest_dict = _read_digest_file(digest_file)
            digest_dict['methods'][self.qualified_name] = {'method': self.digest, 'contract': self.contract_digest}
            digest_file.write_text(json.dumps(digest_dict, indent=4))

            _LOGGER.info(f'Updated method {self.qualified_name} in digest file: {digest_file}')

        @cached_property
        def digest(self) -> str:
            ast = json.dumps(self.ast, sort_keys=True) if self.ast is not None else {}
            contract_digest = self.contract_digest if not self.is_setup else {}
            return hash_str(f'{self.signature}{ast}{self.contract_storage_digest}{contract_digest}')

        def compute_calldata(
            self, contract_name: str, enums: dict[str, int]
        ) -> tuple[KInner, tuple[KInner, ...]] | None:
            prod_klabel = self.unique_klabel
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

                        components = tuple(Input.process_tuple_array(input))

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
                if input.internal_type is not None and input.internal_type.startswith('enum '):
                    enum_name = input.internal_type.split(' ')[1]
                    if enum_name not in enums:
                        _LOGGER.info(
                            f'Skipping adding constraint for {enum_name} because it is not tracked by Kontrol. It can be automatically constrained to its possible values by adding --enum-constraints.'
                        )
                    else:
                        enum_max = enums[enum_name]
                        conjuncts.append(
                            ltInt(
                                KVariable(input.arg_name),
                                intToken(enum_max),
                            )
                        )
            rhs = KEVM.abi_calldata(self.name, args)
            return rhs, tuple(conjuncts)

        @cached_property
        def callvalue_cell(self) -> KInner:
            return intToken(0) if not self.payable else KVariable('CALLVALUE')

        def constrained_calldata(self, contract: Contract, enums: dict[str, int]) -> tuple[KInner, tuple[KInner, ...]]:
            calldata = self.compute_calldata(contract_name=contract.name_with_path, enums=enums)
            if calldata is None:
                raise ValueError(f'Could not compute calldata for: {contract.name_with_path}.{self.name}')
            return calldata

    _name: str
    contract_json: dict
    contract_id: int
    contract_path: str
    deployed_bytecode: str
    immutable_ranges: list[tuple[int, int]]
    link_ranges: list[tuple[int, int]]
    bytecode_external_lib_refs: dict[str, list[tuple[int, int]]]
    deployed_bytecode_external_lib_refs: dict[str, list[tuple[int, int]]]
    processed_link_refs: bool
    bytecode: str
    methods: tuple[Method, ...]
    constructor: Constructor | None
    interface_annotations: dict[str, str]
    error_selectors: dict[bytes, tuple[str, list[str]]]
    PREFIX_CODE: Final = 'Z'

    def __init__(self, contract_name: str, contract_json: dict, foundry: bool = False) -> None:
        self._name = contract_name
        self.contract_json = contract_json

        self.contract_id = self.contract_json['id']
        try:
            self.contract_path = self.contract_json['ast']['absolutePath']
        except KeyError:
            raise ValueError(
                "Must have 'ast' field in solc output. Make sure `ast = true` is present in foundry.toml and run `forge clean`"
            ) from None

        evm = self.contract_json['evm'] if not foundry else self.contract_json

        deployed_bytecode = evm['deployedBytecode']
        bytecode = evm['bytecode']

        self.immutable_ranges = [
            (rng['start'], rng['length'])
            for ref in deployed_bytecode.get('immutableReferences', {}).values()
            for rng in ref
        ]

        self.bytecode_external_lib_refs = {}
        self.deployed_bytecode_external_lib_refs = {}
        self.link_ranges = []

        def process_references(bytecode: dict, target_lib_refs: dict, update_link_ranges: bool = False) -> None:
            for path, references in bytecode.get('linkReferences', {}).items():
                for contract_name, ranges in references.items():
                    ref_name_with_path = contract_name_with_path(path, contract_name)
                    ranges = [(rng['start'], rng['length']) for rng in ranges]

                    target_lib_refs.setdefault(ref_name_with_path, []).extend(ranges)

                    if update_link_ranges:
                        self.link_ranges.extend(ranges)

        process_references(bytecode, self.bytecode_external_lib_refs)
        process_references(deployed_bytecode, self.deployed_bytecode_external_lib_refs, update_link_ranges=True)

        # `deployed_bytecode_external_lib_refs` is a subset of `bytecode_external_lib_refs`
        self.processed_link_refs = len(self.bytecode_external_lib_refs) == 0

        self.deployed_bytecode = deployed_bytecode['object'].replace('0x', '')

        self.bytecode = bytecode['object'].replace('0x', '')
        self.constructor = None

        contract_ast_nodes = [
            (node, node.get('contractKind'))
            for node in self.contract_json['ast']['nodes']
            if node['nodeType'] == 'ContractDefinition' and node['name'] == self._name
        ]
        contract_ast, contract_kind = (
            single(contract_ast_nodes) if len(contract_ast_nodes) > 0 else ({'nodes': []}, None)
        )
        function_asts = {
            node['functionSelector']: node
            for node in contract_ast['nodes']
            if node['nodeType'] == 'FunctionDefinition' and 'functionSelector' in node
        }

        _methods = []
        metadata = self.contract_json.get('metadata', {})
        devdoc = metadata.get('output', {}).get('devdoc', {}).get('methods', {})

        self.interface_annotations = {
            node['name']: node.get('documentation', {}).get('text', '').split()[1]
            for node in contract_ast['nodes']
            if node['nodeType'] == 'VariableDeclaration'
            and 'stateVariable' in node
            and node.get('documentation', {}).get('text', '').startswith('@custom:kontrol-instantiate-interface')
        }

        self.error_selectors = {
            bytes.fromhex(node['errorSelector']): (
                node['name'],
                [param['typeDescriptions']['typeString'] for param in node['parameters']['parameters']],
            )
            for node in contract_ast['nodes']
            if node['nodeType'] == 'ErrorDefinition'
        }

        for method in contract_json['abi']:
            if method['type'] == 'function':
                msig = method_sig_from_abi(method, contract_kind == 'library')
                method_selector: str = str(evm['methodIdentifiers'][msig])
                mid = int(method_selector, 16)
                method_ast = function_asts[method_selector] if method_selector in function_asts else {}
                method_devdoc = devdoc.get(msig)
                method_calls = find_function_calls(method_ast, self.fields)
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

    @cached_property
    def name_with_path(self) -> str:
        return contract_name_with_path(self.contract_path, self._name)

    @cached_property
    def digest(self) -> str:
        return hash_str(f'{self.name_with_path} - {json.dumps(self.contract_json, sort_keys=True)}')

    @cached_property
    def storage_digest(self) -> str:
        storage_layout = self.contract_json.get('storageLayout') or {}
        return hash_str(f'{self.name_with_path} - {json.dumps(storage_layout, sort_keys=True)}')

    @cached_property
    def fields(self) -> tuple[StorageField, ...]:
        return process_storage_layout(self.contract_json.get('storageLayout', {}), self.interface_annotations)

    @cached_property
    def has_storage_layout(self) -> bool:
        return 'storageLayout' in self.contract_json

    @cached_property
    def is_test_contract(self) -> bool:
        return any(field.label == 'IS_TEST' for field in self.fields)

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
    def sort_method(self) -> KSort:
        return KSort(f'{Contract.escaped(self.name_with_path, "S2K")}Method')

    @property
    def klabel(self) -> KLabel:
        return KLabel(f'contract_{self.name_with_path}')

    @property
    def method_by_name(self) -> dict[str, Contract.Method]:
        return {method.name: method for method in self.methods}

    @property
    def method_by_sig(self) -> dict[str, Contract.Method]:
        return {method.signature: method for method in self.methods}


# Helpers


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


def method_sig_from_abi(method_json: dict, is_library: bool = False) -> str:
    def unparse_input(input_json: dict) -> str:
        array_sizes = []
        base_type = input_json['type']
        while re.match(r'.+\[.*\]', base_type):
            array_size_str = base_type.split('[')[1][:-1]
            array_sizes.append(array_size_str if array_size_str != '' else '')
            base_type = base_type.rpartition('[')[0]
        if base_type == 'tuple':
            # If the contract is a library, structs are not unpacked
            if not is_library:
                input_type = '('
                for i, component in enumerate(input_json['components']):
                    if i != 0:
                        input_type += ','
                    input_type += unparse_input(component)
                input_type += ')'
            else:
                input_type = input_json['internalType'].split(' ')[1]
        else:
            input_type = base_type
        for array_size in reversed(array_sizes):
            input_type += f'[{array_size}]' if array_size else '[]'
        return input_type

    method_name = method_json['name']
    method_args = ''
    for i, _input in enumerate(method_json['inputs']):
        if i != 0:
            method_args += ','
        method_args += unparse_input(_input)
    return f'{method_name}({method_args})'


def find_function_calls(node: dict, fields: tuple[StorageField, ...]) -> list[str]:
    """Recursive function that takes a method AST and a set of storage fields and returns all the functions that are called in the given method.

    :param node: AST of a Solidity Method
    :type node: dict
    :param fields: A tuple of contract's fields, including those with interface and contract types.
    :type fields: tuple[StorageField, ...]
    :return: A list of unique function signatures that are called inside the provided method AST.
    :rtype: list[str]

    If a function call is made to an interface which has a user-supplied contract annotation, the function call is considered to belong to this contract.
    Functions that belong to contracts such as `Vm` and `KontrolCheatsBase` are ignored.
    Functions like `abi.encodePacked` that do not belong to a Contract are assigned to a `UnknownContractType` and are ignored.
    """
    function_calls: list[str] = []

    def _is_event(expression: dict) -> bool:
        return expression['typeDescriptions'].get('typeIdentifier', '').startswith('t_function_event')

    def _find_function_calls(node: dict) -> None:
        if not node:
            return

        if node.get('nodeType') == 'FunctionCall':
            expression = node.get('expression', {})
            if expression.get('nodeType', '') == 'MemberAccess' and not _is_event(expression):
                contract_name = expression['expression'].get('name', '')
                contract_type_string = expression['expression']['typeDescriptions'].get('typeString', '')
                contract_type = (
                    contract_type_string.split()[-1] if 'contract' in contract_type_string else 'UnknownContractType'
                )

                for field in fields:
                    if field.label == contract_name and field.linked_interface is not None:
                        contract_type = field.linked_interface
                        break

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


def _contract_name_from_bytecode(
    bytecode: bytes, contracts: dict[str, tuple[str, list[tuple[int, int]], list[tuple[int, int]]]]
) -> str | None:
    for contract_name, (contract_deployed_bytecode, immutable_ranges, link_ranges) in contracts.items():
        zeroed_bytecode = bytearray(bytecode)
        deployed_bytecode_str = re.sub(
            pattern='__\\$(.){34}\\$__',
            repl='0000000000000000000000000000000000000000',
            string=contract_deployed_bytecode,
        )
        deployed_bytecode = bytearray.fromhex(deployed_bytecode_str)

        for start, length in immutable_ranges + link_ranges:
            if start + length <= len(zeroed_bytecode):
                zeroed_bytecode[start : start + length] = bytearray(length)
            else:
                break
        if zeroed_bytecode == deployed_bytecode:
            return contract_name
    return None


def process_storage_layout(storage_layout: dict, interface_annotations: dict) -> tuple[StorageField, ...]:
    storage = storage_layout.get('storage', [])
    types = storage_layout.get('types', {})

    fields_list: list[StorageField] = []
    for field in storage:
        try:
            type_info = types.get(field['type'], {})
            storage_field = StorageField(
                label=field['label'],
                data_type=type_info.get('label', field['type']),
                slot=int(field['slot']),
                offset=int(field['offset']),
                linked_interface=interface_annotations.get(field['label'], None),
            )
            fields_list.append(storage_field)
        except (KeyError, ValueError) as e:
            _LOGGER.error(f'Error processing field {field}: {e}')

    return tuple(fields_list)


def contract_name_with_path(contract_path: str, contract_name: str) -> str:
    contract_path_without_filename = '%'.join(contract_path.split('/')[0:-1])
    return (
        contract_name if contract_path_without_filename == '' else contract_path_without_filename + '%' + contract_name
    )


def decode_kinner_output(
    output: KInner, pretty_output: str, contract_errors: dict[bytes, tuple[str, list[str]]]
) -> str:
    """Decode EVM revert reason using eth-abi"""
    if type(output) is KToken:
        output_bytes: bytes = ast.literal_eval(output.token)
        return parse_output(output_bytes, contract_errors)
    elif type(output) is KApply:
        return parse_composed_output(pretty_output, contract_errors)
    else:
        return pretty_output


def parse_composed_output(pretty_output: str, contract_errors: dict[bytes, tuple[str, list[str]]]) -> str:
    """
    Parse pretty-printed K output to extract meaningful error messages from composed byte sequences.

    Handles mixed concrete byte strings and symbolic K terms by splitting on '+Bytes' delimiter,
    decoding concrete error data, and wrapping symbolic terms in backticks.

    :param pretty_output: Pretty-printed string representation of the OUTPUT_CELL.
    :param contract_errors: Dictionary mapping 4-byte error selectors to (error_name, param_types) tuples
    :return: Space-separated string with decoded error messages and backtick-wrapped K terms
    """

    splits = pretty_output.split('+Bytes')
    result = []

    for item in splits:
        item = item.strip()
        if not item:
            continue

        if item.startswith('b"'):
            try:
                item_bytes = ast.literal_eval(item)
            except (ValueError, SyntaxError):
                # Treat malformed bytes as K term
                escaped_term = item.replace('`', '\\`')
                result.append(f'`{escaped_term}`')
                continue

            if len(item_bytes) < 4:
                decoded = decode_raw_bytes(item_bytes)
                if decoded:
                    result.append(decoded)
                continue

            sig = item_bytes[:4]

            # Map signature to (label, data_slice)
            if sig in contract_errors:
                label, data = contract_errors[sig][0], item_bytes[4:]
            elif sig == GENERIC_ERROR_SELECTOR:
                label, data = 'Error:', item_bytes[4:]
            elif sig == GENERIC_PANIC_SELECTOR:
                label, data = 'Panic:', item_bytes[4:]
            else:
                label, data = None, item_bytes

            if label:
                result.append(label)

            decoded = decode_raw_bytes(data)
            if decoded:
                result.append(decoded)
        else:
            escaped_term = item.replace('`', '\\`')
            result.append(f'`{escaped_term}`')

    return ' '.join(result)


def parse_output(output: bytes, contract_errors: dict[bytes, tuple[str, list[str]]]) -> str:
    """Parse a bytes object representing the EVM output"""

    if len(output) < 4:
        return 'No revert reason'

    selector = output[:4]

    # Error(string) selector
    if selector == GENERIC_ERROR_SELECTOR:
        decoded = decode(['string'], output[4:])
        return decoded[0]

    # Panic(uint256) selector
    elif selector == GENERIC_PANIC_SELECTOR:
        decoded = decode(['uint256'], output[4:])
        panic_code = decoded[0]
        return PANIC_REASONS.get(panic_code, f'Panic code: 0x{panic_code:02x}')

    # User defined errors
    elif selector in contract_errors:
        (error_name, args) = contract_errors[selector]
        decoded = decode(args, output[4:])
        return f'{error_name}{decoded}'

    # Otherwise, decode raw bytes as utf-8 and remove null characters and extra whitespace.
    else:
        return decode_raw_bytes(output)


def decode_raw_bytes(input: bytes) -> str:
    """Otherwise, decode raw bytes as utf-8 and remove null characters and extra whitespace"""
    result = input.decode('utf-8', errors='ignore')
    return ''.join(char for char in result if char != '\x00' and char.isprintable() or char.isspace()).strip()


# Panic codes from https://docs.soliditylang.org/en/latest/control-structures.html#panic-via-assert-and-error-via-require
PANIC_REASONS: Final[dict] = {
    0x00: 'Generic compiler-inserted panic',
    0x01: 'Assertion failed - assert() condition was false',
    0x11: 'Arithmetic overflow/underflow outside unchecked block',
    0x12: 'Division by zero or modulo by zero',
    0x21: 'Enum conversion out of bounds',
    0x22: 'Corrupted storage byte array encoding',
    0x31: 'Pop operation on empty array',
    0x32: 'Array access out of bounds or negative index',
    0x41: 'Memory allocation exceeds limit',
    0x51: 'Call to uninitialized internal function',
}

GENERIC_ERROR_SELECTOR: Final[bytes] = b'\x08\xc3\x79\xa0'
GENERIC_PANIC_SELECTOR: Final[bytes] = b'\x4e\x48\x7b\x71'
