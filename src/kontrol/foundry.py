from __future__ import annotations

import ast
import datetime
import json
import logging
import os
import re
import shutil
import sys
import traceback
import xml.etree.ElementTree as Et
from functools import cached_property
from os import listdir
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import tomlkit
from kevm_pyk.kevm import KEVM, KEVMNodePrinter, KEVMSemantics
from kevm_pyk.utils import byte_offset_to_lines, legacy_explore, print_failure_info, print_model
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KInner, KSort, KToken, KVariable
from pyk.kast.manip import cell_label_to_var_name, collect, extract_lhs, flatten_label, minimize_term, top_down
from pyk.kast.outer import KDefinition, KFlatModule, KImport, KRequire
from pyk.kcfg import KCFG
from pyk.prelude.bytes import bytesToken
from pyk.prelude.collections import map_empty
from pyk.prelude.k import DOTS
from pyk.prelude.kbool import notBool
from pyk.prelude.kint import INT, intToken
from pyk.prelude.ml import mlEqualsFalse, mlEqualsTrue
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.proof.show import APRProofNodePrinter, APRProofShow
from pyk.utils import ensure_dir_path, hash_str, run_process_2, single, unique

from . import VERSION
from .solc_to_k import Contract, _contract_name_from_bytecode
from .state_record import RecreateState, StateDiffEntry, StateDumpEntry
from .utils import (
    _read_digest_file,
    append_to_file,
    empty_lemmas_file_contents,
    foundry_toml_extra_contents,
    kontrol_file_contents,
    kontrol_toml_file_contents,
    kontrol_up_to_date,
    write_to_file,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, Final

    from pyk.kast.outer import KAst
    from pyk.kcfg.kcfg import NodeIdLike
    from pyk.kcfg.tui import KCFGElem
    from pyk.proof.implies import RefutationProof
    from pyk.proof.show import NodePrinter
    from pyk.utils import BugReport

    from .options import (
        CleanOptions,
        GetModelOptions,
        LoadStateOptions,
        MergeNodesOptions,
        MinimizeProofOptions,
        RefuteNodeOptions,
        RemoveNodeOptions,
        SectionEdgeOptions,
        ShowOptions,
        SimplifyNodeOptions,
        SplitNodeOptions,
        StepNodeOptions,
        ToDotOptions,
        UnrefuteNodeOptions,
    )


_LOGGER: Final = logging.getLogger(__name__)


class FoundryKEVM(KEVM):
    foundry: Foundry

    def __init__(
        self,
        definition_dir: Path,
        foundry: Foundry,
        main_file: Path | None = None,
        use_directory: Path | None = None,
        kprove_command: str = 'kprove',
        krun_command: str = 'krun',
        extra_unparsing_modules: Iterable[KFlatModule] = (),
        bug_report: BugReport | None = None,
        use_hex: bool = False,
    ) -> None:
        self.foundry = foundry
        super().__init__(
            definition_dir,
            main_file,
            use_directory,
            kprove_command,
            krun_command,
            extra_unparsing_modules,
            bug_report,
            use_hex,
        )

    def pretty_print(
        self, kast: KAst, *, in_module: str | None = None, unalias: bool = True, sort_collections: bool = False
    ) -> str:
        def _simplify_config(_term: KInner) -> KInner:
            if type(_term) is KApply and _term.is_cell:
                # Show contract names instead of code where available
                if cell_label_to_var_name(_term.label.name) in ['CODE_CELL', 'PROGRAM_CELL']:
                    if type(_term.args[0]) is KToken:
                        contract_name = self.foundry.contract_name_from_bytecode(ast.literal_eval(_term.args[0].token))
                        if contract_name is not None:
                            new_term = KApply(_term.label, [KToken(contract_name, KSort('Bytes'))])
                            return new_term
                hidden_cells = ['JUMPDESTS_CELL', 'INTERIMSTATES_CELL']
                # Hide large, uninformative cells
                if cell_label_to_var_name(_term.label.name) in hidden_cells:
                    return KApply(_term.label, [DOTS])
            return _term

        if not self.foundry._expand_config and isinstance(kast, KInner) and not self.use_hex_encoding:
            kast = top_down(_simplify_config, kast)

        return super().pretty_print(kast, in_module=in_module, unalias=unalias, sort_collections=sort_collections)


class Foundry:
    _root: Path
    _toml: dict[str, Any]
    _bug_report: BugReport | None
    _use_hex_encoding: bool
    _expand_config: bool

    add_enum_constraints: bool
    enums: dict[str, int]

    class Sorts:
        FOUNDRY_CELL: Final = KSort('FoundryCell')

    def __init__(
        self,
        foundry_root: Path,
        bug_report: BugReport | None = None,
        use_hex_encoding: bool = False,
        add_enum_constraints: bool = False,
        expand_config: bool = False,
    ) -> None:
        self._root = foundry_root
        with (foundry_root / 'foundry.toml').open('rb') as f:
            self._toml = tomlkit.load(f)
        self._bug_report = bug_report
        self._use_hex_encoding = use_hex_encoding
        self._expand_config = expand_config
        self.add_enum_constraints = add_enum_constraints
        self.enums = {}

    def lookup_full_contract_name(self, contract_name: str) -> str:
        contracts = [
            full_contract_name
            for full_contract_name in self.contracts
            if contract_name == full_contract_name.split('%')[-1]
        ]
        if len(contracts) == 0:
            raise ValueError(
                f"Tried to look up contract name {contract_name}, found none out of {[contract_name_with_path.split('/')[-1] for contract_name_with_path in self.contracts.keys()]}"
            )
        if len(contracts) > 1:
            raise ValueError(
                f'Tried to look up contract name {contract_name}, found duplicates {[contract[0] for contract in contracts]}'
            )
        return single(contracts)

    @property
    def profile(self) -> dict[str, Any]:
        profile_name = os.getenv('FOUNDRY_PROFILE', default='default')
        return self._toml['profile'][profile_name]

    @property
    def out(self) -> Path:
        return self._root / self.profile.get('out', '')

    @property
    def proofs_dir(self) -> Path:
        return self.out / 'proofs'

    @property
    def digest_file(self) -> Path:
        return self.out / 'digest'

    @property
    def kompiled(self) -> Path:
        return self.out / 'kompiled'

    @property
    def llvm_library(self) -> Path:
        return self.kompiled / 'llvm-library'

    @property
    def main_file(self) -> Path:
        return self.kompiled / 'foundry.k'

    @property
    def contracts_file(self) -> Path:
        return self.kompiled / 'contracts.k'

    @cached_property
    def kevm(self) -> KEVM:
        use_directory = self.out / 'tmp'
        ensure_dir_path(use_directory)
        return FoundryKEVM(
            definition_dir=self.kompiled,
            foundry=self,
            main_file=self.main_file,
            use_directory=use_directory,
            bug_report=self._bug_report,
            use_hex=self._use_hex_encoding,
        )

    @cached_property
    def contracts(self) -> dict[str, Contract]:
        pattern = '**/*.sol/*.json'
        paths = self.out.glob(pattern)
        json_paths = [str(path) for path in paths]
        json_paths = [json_path for json_path in json_paths if not json_path.endswith('.metadata.json')]
        json_paths = sorted(json_paths)  # Must sort to get consistent output order on different platforms
        _LOGGER.info(f'Processing contract files: {json_paths}')
        _contracts: dict[str, Contract] = {}

        for json_path in json_paths:

            def find_enums(dct: dict) -> None:
                if dct['nodeType'] == 'EnumDefinition':
                    enum_name = dct['canonicalName']
                    enum_max = len([member['name'] for member in dct['members']])
                    if enum_name in self.enums and enum_max != self.enums[enum_name]:
                        raise ValueError(
                            f'enum name conflict: {enum_name} exists more than once in the codebase with a different size, which is not supported with --enum-constraints.'
                        )
                    self.enums[enum_name] = len([member['name'] for member in dct['members']])
                for node in dct['nodes']:
                    find_enums(node)

            _LOGGER.debug(f'Processing contract file: {json_path}')
            contract_name = json_path.split('/')[-1]
            contract_json = json.loads(Path(json_path).read_text())
            contract_name = contract_name[0:-5] if contract_name.endswith('.json') else contract_name
            if self.add_enum_constraints:
                find_enums(contract_json['ast'])
            try:
                contract = Contract(contract_name, contract_json, foundry=True)
            except (KeyError, TypeError):
                _LOGGER.warning(f'Skipping non-compatible JSON file for contract: {contract_name} at {json_path}.')
                continue

            _contracts[contract.name_with_path] = contract  # noqa: B909

        return _contracts

    def mk_proofs_dir(self, reinit: bool = False, remove_existing_proofs: bool = False) -> None:
        if remove_existing_proofs and self.proofs_dir.exists():
            self.remove_old_proofs(reinit)
        self.proofs_dir.mkdir(exist_ok=True)

    def method_digest(self, contract_name: str, method_sig: str) -> str:
        return self.contracts[contract_name].method_by_sig[method_sig].digest

    def contract_name_from_bytecode(self, bytecode: bytes) -> str | None:
        return _contract_name_from_bytecode(
            bytecode,
            {
                contract_name: (contract_obj.deployed_bytecode, contract_obj.immutable_ranges, contract_obj.link_ranges)
                for (contract_name, contract_obj) in self.contracts.items()
            },
        )

    @cached_property
    def digest(self) -> str:
        contract_digests = [self.contracts[c].digest for c in sorted(self.contracts)]
        return hash_str('\n'.join(contract_digests))

    @cached_property
    def llvm_dylib(self) -> Path | None:
        match sys.platform:
            case 'linux':
                dylib = self.llvm_library / 'interpreter.so'
            case 'darwin':
                dylib = self.llvm_library / 'interpreter.dylib'
            case _:
                raise ValueError('Unsupported platform: {sys.platform}')

        if dylib.exists():
            return dylib
        else:
            return None

    def up_to_date(self) -> bool:
        if not self.digest_file.exists():
            return False
        digest_dict = _read_digest_file(self.digest_file)
        return digest_dict.get('foundry', '') == self.digest

    def update_digest(self) -> None:
        digest_dict = _read_digest_file(self.digest_file)
        digest_dict['foundry'] = self.digest
        self.digest_file.write_text(json.dumps(digest_dict, indent=4))

        _LOGGER.info(f'Updated Foundry digest file: {self.digest_file}')

    @cached_property
    def contract_ids(self) -> dict[int, str]:
        _contract_ids = {}
        for c in self.contracts.values():
            _contract_ids[c.contract_id] = c.name_with_path
        return _contract_ids

    def srcmap_data(self, contract_name: str, pc: int) -> tuple[Path, int, int] | None:
        if contract_name not in self.contracts:
            _LOGGER.info(f'Contract not found in Foundry project: {contract_name}')
        contract = self.contracts[contract_name]
        if pc not in contract.srcmap:
            _LOGGER.info(f'pc not found in srcmap for contract {contract_name}: {pc}')
            return None
        s, l, f, _, _ = contract.srcmap[pc]
        if f not in self.contract_ids:
            _LOGGER.info(f'Contract id not found in sourcemap data: {f}')
            return None
        src_contract = self.contracts[self.contract_ids[f]]
        src_contract_path = self._root / src_contract.contract_path
        src_contract_text = src_contract_path.read_text()
        _, start, end = byte_offset_to_lines(src_contract_text.split('\n'), s, l)
        return (src_contract_path, start, end)

    def solidity_src(self, contract_name: str, pc: int) -> Iterable[str]:
        srcmap_data = self.srcmap_data(contract_name, pc)
        if srcmap_data is None:
            return [f'No sourcemap data for contract at pc {contract_name}: {pc}']
        contract_path, start, end = srcmap_data
        if not (contract_path.exists() and contract_path.is_file()):
            return [f'No file at path for contract {contract_name}: {contract_path}']
        lines = contract_path.read_text().split('\n')
        prefix_lines = [f'   {l}' for l in lines[:start]]
        actual_lines = [f' | {l}' for l in lines[start:end]]
        suffix_lines = [f'   {l}' for l in lines[end:]]
        return prefix_lines + actual_lines + suffix_lines

    def short_info_for_contract(self, contract_name: str, cterm: CTerm) -> list[str]:
        ret_strs = self.kevm.short_info(cterm)
        _pc = cterm.cell('PC_CELL')
        if type(_pc) is KToken and _pc.sort == INT:
            srcmap_data = self.srcmap_data(contract_name, int(_pc.token))
            if srcmap_data is not None:
                path, start, end = srcmap_data
                ret_strs.append(f'src: {str(path)}:{start}:{end}')
        return ret_strs

    def custom_view(self, contract_name: str, element: KCFGElem) -> Iterable[str]:
        if type(element) is KCFG.Node:
            pc_cell = element.cterm.try_cell('PC_CELL')
            if type(pc_cell) is KToken and pc_cell.sort == INT:
                return self.solidity_src(contract_name, int(pc_cell.token))
        elif type(element) is KCFG.Edge:
            return list(element.rules)
        elif type(element) is KCFG.NDBranch:
            return list(element.rules)
        return ['NO DATA']

    def build(self) -> None:
        try:
            run_process_2(['forge', 'build', '--build-info', '--root', str(self._root)], logger=_LOGGER)
        except FileNotFoundError as err:
            raise RuntimeError(
                "Error: 'forge' command not found. Please ensure that 'forge' is installed and added to your PATH."
            ) from err
        except CalledProcessError as err:
            raise RuntimeError("Couldn't forge build!") from err

    @cached_property
    def all_tests(self) -> list[str]:
        test_dir = os.path.join(self.profile.get('test', 'test'), '')
        return [
            f'{contract.name_with_path}.{method.signature}'
            for contract in self.contracts.values()
            if contract.contract_path.startswith(test_dir)
            for method in contract.methods
            if method.is_test
        ]

    @cached_property
    def all_non_tests(self) -> list[str]:
        return [
            f'{contract.name_with_path}.{method.signature}'
            for contract in self.contracts.values()
            for method in contract.methods
            if f'{contract.name_with_path}.{method.signature}' not in self.all_tests
        ] + [f'{contract.name_with_path}.init' for contract in self.contracts.values() if contract.constructor]

    @staticmethod
    def _escape_brackets(regs: list[str]) -> list[str]:
        regs = [reg.replace('[', '\\[') for reg in regs]
        regs = [reg.replace(']', '\\]') for reg in regs]
        regs = [reg.replace('(', '\\(') for reg in regs]
        return [reg.replace(')', '\\)') for reg in regs]

    @staticmethod
    def _exact_match(regs: list[str]) -> list[str]:
        return [f'(^|%)({reg})$' for reg in regs]

    def matching_tests(self, tests: list[str], exact_match: bool = False) -> list[str]:
        all_tests = self.all_tests
        all_non_tests = self.all_non_tests
        tests = Foundry._escape_brackets(tests)
        tests = Foundry._exact_match(tests) if exact_match else tests
        matched_tests = set()
        unfound_tests = set(tests)
        for test in tests:
            for possible_match in all_tests + all_non_tests:
                if re.search(test, possible_match):
                    matched_tests.add(possible_match)
                    unfound_tests.discard(test)
        if unfound_tests:
            raise ValueError(f'Test identifiers not found: {set(unfound_tests)}')
        elif len(matched_tests) == 0:
            raise ValueError('No test matched the predicates')
        return list(matched_tests)

    def matching_sigs(self, test: str, exact_match: bool = False) -> list[str]:
        test_sigs = self.matching_tests([test], exact_match=exact_match)
        return test_sigs

    def get_test_id(self, test: str, version: int | None) -> str:
        """
        Retrieves the unique identifier for a test based on its name and version.

        If multiple proofs are found for a test without a specific version, the function attempts to resolve to the latest version.

        :param test: The name of the test to find a matching proof for.
        :param version: The version number of the test. If None, the function attempts to resolve to the latest version if multiple matches are found.
        :raises ValueError: If no matching proofs are found for the given test and version, indicating the test does not exist.
        :raises ValueError: If more than one matching proof is found for a given test and version, a full signature is required.
        :return: The unique identifier of the matching proof for the specified test and version.
        """

        def _assert_single_id(l: list[str]) -> str:
            try:
                return single(l)
            except ValueError as e:
                error_msg = (
                    f'Found {len(matching_proof_ids)} matching proofs for {test}:{version}. '
                    f'Provide a full signature of the test, e.g., {matching_sigs[0][5:]!r} --version {version}. '
                    f'Error: {e}'
                )
                raise ValueError(error_msg) from e

        matching_proof_ids = self.proof_ids_with_test(test, version)
        matching_sigs = self.matching_sigs(test)

        if not matching_proof_ids:
            raise ValueError(f'Found no matching proofs for {test}:{version}.')

        _assert_single_id(matching_sigs)

        if len(matching_proof_ids) > 1 and version is None:
            print(
                f'Found {len(matching_proof_ids)} matching proofs for {test}:{version}. Running the latest one. Use the `--version` flag to choose one.'
            )
            latest_version = self.resolve_proof_version(matching_sigs[0], False, version)
            matching_proof_ids = self.proof_ids_with_test(test, latest_version)

        return _assert_single_id(matching_proof_ids)

    @staticmethod
    def success(s: KInner, dst: KInner, r: KInner, c: KInner, e1: KInner, e2: KInner) -> KApply:
        return KApply('foundry_success', [s, dst, r, c, e1, e2])

    @staticmethod
    def fail(s: KInner, dst: KInner, r: KInner, c: KInner, e1: KInner, e2: KInner) -> KApply:
        return notBool(Foundry.success(s, dst, r, c, e1, e2))

    # address(uint160(uint256(keccak256("foundry default caller"))))

    @staticmethod
    def loc_FOUNDRY_FAILED() -> KApply:  # noqa: N802
        return KEVM.loc(
            KApply(
                'contract_access_field',
                [
                    KApply('contract_FoundryCheat'),
                    KApply('slot_failed'),
                ],
            )
        )

    @staticmethod
    def symbolic_contract_prefix() -> str:
        return 'C'

    @staticmethod
    def symbolic_contract_name(contract_name: str) -> str:
        return Foundry.symbolic_contract_prefix() + '_' + contract_name.upper()

    @staticmethod
    def symbolic_contract_id(contract_name: str) -> str:
        return Foundry.symbolic_contract_name(contract_name) + '_ID'

    @staticmethod
    def address_TEST_CONTRACT() -> KToken:  # noqa: N802
        return intToken(0x7FA9385BE102AC3EAC297483DD6233D62B3E1496)

    @staticmethod
    def address_CHEATCODE() -> KToken:  # noqa: N802
        return intToken(0x7109709ECFA91A80626FF3989D68F67F5B1DD12D)

    # Same address as the one used in DappTools's HEVM
    # address(bytes20(uint160(uint256(keccak256('hevm cheat code')))))
    @staticmethod
    def account_CHEATCODE_ADDRESS(store_var: KInner) -> KApply:  # noqa: N802
        return KEVM.account_cell(
            Foundry.address_CHEATCODE(),  # Hardcoded for now
            intToken(0),
            bytesToken(b'\x00'),
            store_var,
            map_empty(),
            map_empty(),
            intToken(0),
        )

    @staticmethod
    def symbolic_account(prefix: str, program: KInner, storage: KInner | None = None) -> KApply:
        return KEVM.account_cell(
            KVariable(prefix + '_ID', sort=KSort('Int')),
            KVariable(prefix + '_BAL', sort=KSort('Int')),
            program,
            storage if storage is not None else KVariable(prefix + '_STORAGE', sort=KSort('Map')),
            KVariable(prefix + '_ORIGSTORAGE', sort=KSort('Map')),
            KVariable(prefix + '_TRANSIENTSTORAGE', sort=KSort('Map')),
            KVariable(prefix + '_NONCE', sort=KSort('Int')),
        )

    @staticmethod
    def help_info() -> list[str]:
        res_lines: list[str] = []
        res_lines.append('')
        res_lines.append('See `foundry_success` predicate for more information:')
        res_lines.append(
            'https://github.com/runtimeverification/kontrol/blob/master/src/kontrol/kdist/foundry.md#foundry-success-predicate'
        )
        res_lines.append('')
        res_lines.append('Access documentation for Kontrol at https://docs.runtimeverification.com/kontrol')
        return res_lines

    @staticmethod
    def filter_proof_ids(proof_ids: list[str], test: str, version: int | None = None) -> list[str]:
        """
        Searches for proof IDs that match a specified test name and an optional version number.

        Each proof ID is expected to follow the format 'proof_dir_1%proof_dir_2%proof_name:version'.
        Only proof IDs that match the given criteria are included in the returned list.
        """
        regex = single(Foundry._escape_brackets([test]))
        matches = []
        for pid in proof_ids:
            try:
                proof_dir, proof_name_version = pid.rsplit('%', 1)
                proof_name, proof_version_str = proof_name_version.split(':', 1)
                proof_dir_name = proof_dir + '%' + proof_name
                proof_version = int(proof_version_str)
            except ValueError:
                continue
            if re.search(regex, proof_dir_name) and (version is None or version == proof_version):
                matches.append(f'{proof_dir}%{proof_name}:{proof_version}')
        return matches

    def proof_ids_with_test(self, test: str, version: int | None = None) -> list[str]:
        proof_ids = self.filter_proof_ids(self.list_proof_dir(), test, version)
        _LOGGER.info(f'Found {len(proof_ids)} matching proofs for {test}:{version}: {proof_ids}')
        return proof_ids

    def get_apr_proof(self, test_id: str) -> APRProof:
        proof = Proof.read_proof_data(self.proofs_dir, test_id)
        if not isinstance(proof, APRProof):
            raise ValueError('Specified proof is not an APRProof.')
        return proof

    def get_proof(self, test_id: str) -> Proof:
        return Proof.read_proof_data(self.proofs_dir, test_id)

    def get_optional_apr_proof(self, test_id: str) -> APRProof | None:
        proof = self.get_optional_proof(test_id)
        if not isinstance(proof, APRProof):
            return None
        return proof

    def get_optional_proof(self, test_id: str) -> Proof | None:
        if Proof.proof_data_exists(test_id, self.proofs_dir):
            return Proof.read_proof_data(self.proofs_dir, test_id)
        return None

    def get_contract_and_method(self, test: str) -> tuple[Contract, Contract.Method | Contract.Constructor]:
        contract_name, method_name = test.split('.')
        contract = self.contracts[contract_name]

        if method_name == 'init':
            constructor = self.contracts[contract_name].constructor
            if constructor is None:
                raise ValueError(f'Contract {contract_name} does not have a constructor.')
            return contract, constructor

        method = contract.method_by_sig[method_name]
        return contract, method

    def list_proof_dir(self) -> list[str]:
        return listdir(self.proofs_dir)

    def resolve_setup_proof_version(
        self, test: str, reinit: bool, test_version: int | None = None, user_specified_setup_version: int | None = None
    ) -> int:
        _, method = self.get_contract_and_method(test)
        effective_test_version = 0 if test_version is None else self.free_proof_version(test)

        if not method.up_to_date(self.digest_file):
            _LOGGER.info(f'Creating a new version of {test} because it was updated.')
            return self.free_proof_version(test)

        if not kontrol_up_to_date(self.digest_file):
            _LOGGER.warning(
                'Kontrol version is different than the one used to generate the current definition. Consider running `kontrol build` to update the definition.'
            )

        if reinit:
            if user_specified_setup_version is None:
                _LOGGER.info(
                    f'Creating a new version of {test} because --reinit was specified and --setup-version is not specified.'
                )
            elif not Proof.proof_data_exists(f'{test}:{user_specified_setup_version}', self.proofs_dir):
                _LOGGER.info(
                    f'Creating a new version of {test} because --reinit was specified and --setup-version is set to a non-existing version'
                )
            else:
                _LOGGER.info(f'Reusing version {user_specified_setup_version} of {test}')
                effective_test_version = user_specified_setup_version
        else:
            latest_test_version = self.latest_proof_version(test)
            effective_test_version = 0 if latest_test_version is None else latest_test_version
            if user_specified_setup_version is not None and Proof.proof_data_exists(
                f'{test}:{user_specified_setup_version}', self.proofs_dir
            ):
                effective_test_version = user_specified_setup_version
            _LOGGER.info(f'Using version {effective_test_version} of {test}')

        return effective_test_version

    def resolve_proof_version(
        self,
        test: str,
        reinit: bool,
        user_specified_version: int | None,
    ) -> int:
        _, method = self.get_contract_and_method(test)

        if reinit and user_specified_version is not None:
            raise ValueError('--reinit is not compatible with specifying proof versions.')

        if reinit:
            _LOGGER.info(f'Creating a new version of test {test} because --reinit was specified.')
            return self.free_proof_version(test)

        if not kontrol_up_to_date(self.digest_file):
            _LOGGER.warning(
                'Kontrol version is different than the one used to generate the current definition. Consider running `kontrol build` to update the definition.'
            )

        method_status = method.up_to_date(self.digest_file)

        if user_specified_version:
            _LOGGER.info(f'Using user-specified version {user_specified_version} for test {test}')
            if not Proof.proof_data_exists(f'{test}:{user_specified_version}', self.proofs_dir):
                raise ValueError(f'The specified version {user_specified_version} of proof {test} does not exist.')
            if not method_status:
                _LOGGER.warn(
                    f'Using specified version {user_specified_version} of proof {test}, but it is out of date.'
                )
            return user_specified_version

        if not method_status:
            _LOGGER.info(f'Creating a new version of test {test} because it is out of date.')
            return self.free_proof_version(test)

        latest_version = self.latest_proof_version(test)
        return self.check_method_change(latest_version, test, method)

    def check_method_change(
        self, version: int | None, test: str, method: Contract.Method | Contract.Constructor
    ) -> int:
        if version is not None:
            _LOGGER.info(
                f'Using the the latest version {version} of test {test} because it is up to date and no version was specified.'
            )
            if type(method) is Contract.Method and not method.contract_up_to_date(self.digest_file):
                _LOGGER.warning(
                    f'Test {test} was not reinitialized because it is up to date, but the contract it is a part of has changed.'
                )
            return version

        _LOGGER.info(
            f'Test {test} is up to date in {self.digest_file}, but does not exist on disk. Assigning version 0'
        )
        return 0

    def latest_proof_version(
        self,
        test: str,
    ) -> int | None:
        """
        find the highest used proof ID, to be used as a default. Returns None if no version of this proof exists.
        """
        proof_ids = self.filter_proof_ids(self.list_proof_dir(), test.split('%')[-1])
        versions = {int(pid.split(':')[1]) for pid in proof_ids}
        return max(versions, default=None)

    def free_proof_version(
        self,
        test: str,
    ) -> int:
        """
        find the lowest proof id that is not used yet
        """
        latest_version = self.latest_proof_version(test)
        return latest_version + 1 if latest_version is not None else 0

    def remove_old_proofs(self, force_remove: bool = False) -> bool:
        if force_remove or any(
            # We need to check only the methods that get written to the digest file
            # Otherwise we'd get vacuous positives
            (method.is_test or method.is_testfail or method.is_setup)
            and not method.contract_up_to_date(Path(self.digest_file))
            for contract in self.contracts.values()
            for method in contract.methods
        ):
            shutil.rmtree(self.proofs_dir.absolute())
            return True
        else:
            return False

    def remove_proofs_dir(self) -> None:
        if self.proofs_dir.exists():
            shutil.rmtree(self.proofs_dir.absolute())


def foundry_show(
    foundry: Foundry,
    options: ShowOptions,
) -> str:
    test_id = foundry.get_test_id(options.test, options.version)
    contract_name, _ = single(foundry.matching_tests([options.test])).split('.')
    proof = foundry.get_apr_proof(test_id)

    nodes: Iterable[int | str] = options.nodes
    if options.pending:
        nodes = list(nodes) + [node.id for node in proof.pending]
    if options.failing:
        nodes = list(nodes) + [node.id for node in proof.failing]
    nodes = unique(nodes)

    unstable_cells = [
        '<program>',
        '<jumpDests>',
        '<pc>',
        '<gas>',
        '<code>',
    ]

    node_printer = foundry_node_printer(
        foundry, contract_name, proof, omit_unstable_output=options.omit_unstable_output
    )
    proof_show = APRProofShow(foundry.kevm, node_printer=node_printer)

    res_lines = proof_show.show(
        proof,
        nodes=nodes,
        node_deltas=options.node_deltas,
        to_module=options.to_module,
        minimize=options.minimize,
        sort_collections=options.sort_collections,
        omit_cells=(unstable_cells if options.omit_unstable_output else []),
    )

    start_server = options.port is None

    if options.failure_info:
        with legacy_explore(
            foundry.kevm,
            kcfg_semantics=KEVMSemantics(),
            id=test_id,
            smt_timeout=options.smt_timeout,
            smt_retry_limit=options.smt_retry_limit,
            start_server=start_server,
            port=options.port,
            maude_port=options.maude_port,
        ) as kcfg_explore:
            res_lines += print_failure_info(proof, kcfg_explore, options.counterexample_info)
            res_lines += Foundry.help_info()

    if options.to_kevm_claims:
        _foundry_labels = [
            prod.klabel
            for prod in foundry.kevm.definition.all_modules_dict['FOUNDRY-CHEAT-CODES'].productions
            if prod.klabel is not None
        ]

        def _remove_foundry_config(_cterm: CTerm) -> CTerm:
            kevm_config_pattern = KApply(
                '<generatedTop>',
                [
                    KApply('<foundry>', [KVariable('KEVM_CELL'), KVariable('CHEATCODES_CELL')]),
                    KVariable('GENERATEDCOUNTER_CELL'),
                ],
            )
            kevm_config_match = kevm_config_pattern.match(_cterm.config)
            if kevm_config_match is None:
                _LOGGER.warning('Unable to match on <kevm> cell.')
                return _cterm
            return CTerm(kevm_config_match['KEVM_CELL'], _cterm.constraints)

        def _contains_foundry_klabel(_kast: KInner) -> bool:
            _contains = False

            def _collect_klabel(_k: KInner) -> None:
                nonlocal _contains
                if type(_k) is KApply and _k.label.name in _foundry_labels:
                    _contains = True

            collect(_collect_klabel, _kast)
            return _contains

        for node in proof.kcfg.nodes:
            proof.kcfg.let_node(node.id, cterm=_remove_foundry_config(node.cterm))

        # Due to bug in KCFG.replace_node: https://github.com/runtimeverification/pyk/issues/686
        proof.kcfg = KCFG.from_dict(proof.kcfg.to_dict())

        claims = [edge.to_rule('BASIC-BLOCK', claim=True) for edge in proof.kcfg.edges()]
        claims = [claim for claim in claims if not _contains_foundry_klabel(claim.body)]
        claims = [
            claim for claim in claims if not KEVMSemantics().is_terminal(CTerm.from_kast(extract_lhs(claim.body)))
        ]
        if len(claims) == 0:
            _LOGGER.warning(f'No claims retained for proof {proof.id}')

        else:
            module_name = Contract.escaped(proof.id.upper() + '-SPEC', '')
            module = KFlatModule(module_name, sentences=claims, imports=[KImport('VERIFICATION')])
            defn = KDefinition(module_name, [module], requires=[KRequire('verification.k')])

            defn_lines = foundry.kevm.pretty_print(defn, in_module='EVM').split('\n')

            res_lines += defn_lines

            if options.kevm_claim_dir is not None:
                kevm_claims_file = options.kevm_claim_dir / (module_name.lower() + '.k')
                kevm_claims_file.write_text('\n'.join(line.rstrip() for line in defn_lines))

    return '\n'.join([line.rstrip() for line in res_lines])


def foundry_to_dot(foundry: Foundry, options: ToDotOptions) -> None:
    dump_dir = foundry.proofs_dir / 'dump'
    test_id = foundry.get_test_id(options.test, options.version)
    contract_name, _ = single(foundry.matching_tests([options.test])).split('.')
    proof = foundry.get_apr_proof(test_id)

    node_printer = foundry_node_printer(foundry, contract_name, proof)
    proof_show = APRProofShow(foundry.kevm, node_printer=node_printer)

    proof_show.dump(proof, dump_dir, dot=True)


def foundry_list(foundry: Foundry) -> list[str]:
    all_methods = [
        f'{contract.name_with_path}.{method.signature}'
        for contract in foundry.contracts.values()
        for method in contract.methods
    ]

    lines: list[str] = []
    for method in sorted(all_methods):
        for test_id in listdir(foundry.proofs_dir):
            test, *_ = test_id.split(':')
            if test == method:
                proof = foundry.get_optional_proof(test_id)
                if proof is not None:
                    lines.extend(proof.summary.lines)
                    lines.append('')
    if len(lines) > 0:
        lines = lines[0:-1]

    return lines


def setup_exec_time(foundry: Foundry, contract: Contract) -> float:
    setup_exec_time = 0.0
    if 'setUp' in contract.method_by_name:
        latest_version = foundry.latest_proof_version(f'{contract.name_with_path}.setUp()')
        setup_digest = f'{contract.name_with_path}.setUp():{latest_version}'
        apr_proof = APRProof.read_proof_data(foundry.proofs_dir, setup_digest)
        setup_exec_time = apr_proof.exec_time
    return setup_exec_time


def foundry_to_xml(foundry: Foundry, proofs: list[APRProof]) -> None:
    testsuites = Et.Element(
        'testsuites', tests='0', failures='0', errors='0', time='0', timestamp=str(datetime.datetime.now())
    )
    tests = 0
    total_exec_time = 0.0
    for proof in proofs:
        tests += 1
        test, *_ = proof.id.split(':')
        contract, test_name = test.split('.')
        _, contract_name = contract.rsplit('%', 1)
        foundry_contract = foundry.contracts[contract]
        contract_path = foundry_contract.contract_path
        proof_exec_time = proof.exec_time
        testsuite = testsuites.find(f'testsuite[@name={contract_name!r}]')
        if testsuite is None:
            proof_exec_time += setup_exec_time(foundry, foundry_contract)
            testsuite = Et.SubElement(
                testsuites,
                'testsuite',
                name=contract_name,
                tests='1',
                failures='0',
                errors='0',
                time=str(proof_exec_time),
                timestamp=str(datetime.datetime.now()),
            )
            properties = Et.SubElement(testsuite, 'properties')
            Et.SubElement(properties, 'property', name='Kontrol version', value=str(VERSION))
        else:
            testsuite_exec_time = float(testsuite.get('time', 0)) + proof_exec_time
            testsuite.set('time', str(testsuite_exec_time))
            testsuite.set('tests', str(int(testsuite.get('tests', 0)) + 1))

        total_exec_time += proof_exec_time
        testcase = Et.SubElement(
            testsuite,
            'testcase',
            name=test_name,
            classname=contract_name,
            time=str(proof_exec_time),
            file=contract_path,
        )

        if not proof.passed:
            if proof.error_info is not None:
                error = Et.SubElement(testcase, 'error', message='Exception')
                trace = traceback.format_exception(proof.error_info)
                error.set('type', str(type(proof.error_info).__name__))
                error.text = '\n' + ' '.join(trace)
                testsuite.set('errors', str(int(testsuite.get('errors', 0)) + 1))
                testsuites.set('errors', str(int(testsuites.get('errors', 0)) + 1))
            else:
                if proof.failure_info is not None and isinstance(proof.failure_info, APRFailureInfo):
                    failure = Et.SubElement(testcase, 'failure', message='Proof failed')
                    text = proof.failure_info.print()
                    failure.set('message', text[0])
                    failure.text = '\n'.join(text[1:-1])
                    testsuite.set('failures', str(int(testsuite.get('failures', 0)) + 1))
                    testsuites.set('failures', str(int(testsuites.get('failures', 0)) + 1))

    testsuites.set('tests', str(tests))
    testsuites.set('time', str(total_exec_time))
    tree = Et.ElementTree(testsuites)
    Et.indent(tree, space='\t', level=0)
    tree.write('kontrol_prove_report.xml')


def foundry_minimize_proof(foundry: Foundry, options: MinimizeProofOptions) -> None:
    test_id = foundry.get_test_id(options.test, options.version)
    apr_proof = foundry.get_apr_proof(test_id)
    apr_proof.minimize_kcfg()
    apr_proof.write_proof_data()


def foundry_remove_node(foundry: Foundry, options: RemoveNodeOptions) -> None:
    test_id = foundry.get_test_id(options.test, options.version)
    apr_proof = foundry.get_apr_proof(test_id)
    node_ids = apr_proof.prune(options.node)
    _LOGGER.info(f'Pruned nodes: {node_ids}')
    apr_proof.write_proof_data()


def foundry_refute_node(
    foundry: Foundry,
    options: RefuteNodeOptions,
) -> RefutationProof | None:
    test_id = foundry.get_test_id(options.test, options.version)
    proof = foundry.get_apr_proof(test_id)

    return proof.refute_node(proof.kcfg.node(options.node))


def foundry_unrefute_node(foundry: Foundry, options: UnrefuteNodeOptions) -> None:
    test_id = foundry.get_test_id(options.test, options.version)
    proof = foundry.get_apr_proof(test_id)

    proof.unrefute_node(proof.kcfg.node(options.node))


def foundry_split_node(
    foundry: Foundry,
    options: SplitNodeOptions,
) -> list[int]:
    contract_name, _ = single(foundry.matching_tests([options.test])).split('.')
    test_id = foundry.get_test_id(options.test, options.version)
    proof = foundry.get_apr_proof(test_id)

    token = KToken(options.branch_condition, 'Bool')
    node_printer = foundry_node_printer(foundry, contract_name, proof)
    parsed_condition = node_printer.kprint.parse_token(token, as_rule=True)

    split_nodes = proof.kcfg.split_on_constraints(
        options.node, [mlEqualsTrue(parsed_condition), mlEqualsFalse(parsed_condition)]
    )
    _LOGGER.info(f'Split node {options.node} into {split_nodes} on branch condition {options.branch_condition}')
    proof.write_proof_data()

    return split_nodes


def foundry_simplify_node(
    foundry: Foundry,
    options: SimplifyNodeOptions,
) -> str:
    test_id = foundry.get_test_id(options.test, options.version)
    apr_proof = foundry.get_apr_proof(test_id)
    cterm = apr_proof.kcfg.node(options.node).cterm
    start_server = options.port is None

    kore_rpc_command = None
    if isinstance(options.kore_rpc_command, str):
        kore_rpc_command = options.kore_rpc_command.split()

    with legacy_explore(
        foundry.kevm,
        kcfg_semantics=KEVMSemantics(),
        id=apr_proof.id,
        bug_report=options.bug_report,
        kore_rpc_command=kore_rpc_command,
        llvm_definition_dir=foundry.llvm_library if options.use_booster else None,
        smt_timeout=options.smt_timeout,
        smt_retry_limit=options.smt_retry_limit,
        smt_tactic=options.smt_tactic,
        log_succ_rewrites=options.log_succ_rewrites,
        log_fail_rewrites=options.log_fail_rewrites,
        start_server=start_server,
        port=options.port,
        maude_port=options.maude_port,
    ) as kcfg_explore:
        new_term, _ = kcfg_explore.cterm_symbolic.simplify(cterm)
    if options.replace:
        apr_proof.kcfg.let_node(options.node, cterm=new_term)
        apr_proof.write_proof_data()
    res_term = minimize_term(new_term.kast) if options.minimize else new_term.kast
    return foundry.kevm.pretty_print(res_term, unalias=False, sort_collections=options.sort_collections)


def foundry_merge_nodes(
    foundry: Foundry,
    options: MergeNodesOptions,
) -> None:
    def check_cells_equal(cell: str, nodes: Iterable[KCFG.Node]) -> bool:
        nodes = list(nodes)
        if len(nodes) < 2:
            return True
        cell_value = nodes[0].cterm.try_cell(cell)
        if cell_value is None:
            return False
        for node in nodes[1:]:
            if node.cterm.try_cell(cell) is None or cell_value != node.cterm.cell(cell):
                return False
        return True

    test_id = foundry.get_test_id(options.test, options.version)
    apr_proof = foundry.get_apr_proof(test_id)

    if len(list(options.nodes)) < 2:
        raise ValueError(f'Must supply at least 2 nodes to merge, got: {options.nodes}')

    nodes = [apr_proof.kcfg.node(int(node_id)) for node_id in options.nodes]
    check_cells = ['K_CELL', 'PROGRAM_CELL', 'PC_CELL', 'CALLDEPTH_CELL']
    check_cells_ne = [check_cell for check_cell in check_cells if not check_cells_equal(check_cell, nodes)]

    if check_cells_ne:
        if not all(KEVMSemantics().same_loop(nodes[0].cterm, nd.cterm) for nd in nodes):
            raise ValueError(f'Nodes {options.nodes} cannot be merged because they differ in: {check_cells_ne}')

    anti_unification = nodes[0].cterm
    for node in nodes[1:]:
        anti_unification, _, _ = anti_unification.anti_unify(node.cterm, keep_values=True, kdef=foundry.kevm.definition)
    new_node = apr_proof.kcfg.create_node(anti_unification)
    for node in nodes:
        succ = apr_proof.kcfg.successors(node.id)
        if len(succ) == 0:
            apr_proof.kcfg.create_cover(node.id, new_node.id)
        else:
            apr_proof.prune(node.id, keep_nodes=[node.id])
            apr_proof.kcfg.create_cover(node.id, new_node.id)

    apr_proof.write_proof_data()

    print(f'Merged nodes {options.nodes} into new node {new_node.id}.')
    print(foundry.kevm.pretty_print(new_node.cterm.kast))


def foundry_step_node(
    foundry: Foundry,
    options: StepNodeOptions,
) -> None:
    if options.repeat < 1:
        raise ValueError(f'Expected positive value for --repeat, got: {options.repeat}')
    if options.depth < 1:
        raise ValueError(f'Expected positive value for --depth, got: {options.depth}')

    test_id = foundry.get_test_id(options.test, options.version)
    apr_proof = foundry.get_apr_proof(test_id)
    start_server = options.port is None

    kore_rpc_command = None
    if isinstance(options.kore_rpc_command, str):
        kore_rpc_command = options.kore_rpc_command.split()

    with legacy_explore(
        foundry.kevm,
        kcfg_semantics=KEVMSemantics(),
        id=apr_proof.id,
        bug_report=options.bug_report,
        kore_rpc_command=kore_rpc_command,
        llvm_definition_dir=foundry.llvm_library if options.use_booster else None,
        smt_timeout=options.smt_timeout,
        smt_retry_limit=options.smt_retry_limit,
        smt_tactic=options.smt_tactic,
        log_succ_rewrites=options.log_succ_rewrites,
        log_fail_rewrites=options.log_fail_rewrites,
        start_server=start_server,
        port=options.port,
        maude_port=options.maude_port,
    ) as kcfg_explore:
        node = options.node
        for _i in range(options.repeat):
            node = kcfg_explore.step(apr_proof.kcfg, node, apr_proof.logs, depth=options.depth)
            apr_proof.write_proof_data()


def foundry_state_load(options: LoadStateOptions, foundry: Foundry) -> None:
    accounts = read_contract_names(options.contract_names) if options.contract_names else {}
    recreate_state_contract = RecreateState(name=options.name, accounts=accounts)
    if options.from_state_diff:
        access_entries = read_recorded_state_diff(options.accesses_file)
        for access in access_entries:
            recreate_state_contract.extend_with_state_diff(access)
    else:
        recorded_accounts = read_recorded_state_dump(options.accesses_file)
        for account in recorded_accounts:
            recreate_state_contract.extend_with_state_dump(account)

    output_dir_name = options.output_dir_name
    if output_dir_name is None:
        output_dir_name = foundry.profile.get('test', '')

    output_dir = foundry._root / output_dir_name
    ensure_dir_path(output_dir)

    main_file = output_dir / Path(options.name + '.sol')

    if not options.license.strip():
        raise ValueError('License cannot be empty or blank')

    if options.condense_state_diff:
        main_file.write_text(
            '\n'.join(recreate_state_contract.generate_condensed_file(options.comment_generated_file, options.license))
        )
    else:
        code_file = output_dir / Path(options.name + 'Code.sol')
        main_file.write_text(
            '\n'.join(
                recreate_state_contract.generate_main_contract_file(options.comment_generated_file, options.license)
            )
        )
        code_file.write_text(
            '\n'.join(
                recreate_state_contract.generate_code_contract_file(options.comment_generated_file, options.license)
            )
        )


def foundry_section_edge(
    foundry: Foundry,
    options: SectionEdgeOptions,
) -> None:
    test_id = foundry.get_test_id(options.test, options.version)
    apr_proof = foundry.get_apr_proof(test_id)
    source_id, target_id = options.edge
    start_server = options.port is None

    kore_rpc_command = None
    if isinstance(options.kore_rpc_command, str):
        kore_rpc_command = options.kore_rpc_command.split()

    with legacy_explore(
        foundry.kevm,
        kcfg_semantics=KEVMSemantics(),
        id=apr_proof.id,
        bug_report=options.bug_report,
        kore_rpc_command=kore_rpc_command,
        llvm_definition_dir=foundry.llvm_library if options.use_booster else None,
        smt_timeout=options.smt_timeout,
        smt_retry_limit=options.smt_retry_limit,
        smt_tactic=options.smt_tactic,
        log_succ_rewrites=options.log_succ_rewrites,
        log_fail_rewrites=options.log_fail_rewrites,
        start_server=start_server,
        port=options.port,
        maude_port=options.maude_port,
    ) as kcfg_explore:
        kcfg_explore.section_edge(
            apr_proof.kcfg,
            source_id=int(source_id),
            target_id=int(target_id),
            logs=apr_proof.logs,
            sections=options.sections,
        )
    apr_proof.write_proof_data()


def foundry_get_model(
    foundry: Foundry,
    options: GetModelOptions,
) -> str:
    test_id = foundry.get_test_id(options.test, options.version)
    proof = foundry.get_apr_proof(test_id)

    if not options.nodes:
        _LOGGER.warning('Node ID is not provided. Displaying models of failing and pending nodes:')
        failing = pending = True

    nodes: Iterable[NodeIdLike] = options.nodes
    if pending:
        nodes = list(nodes) + [node.id for node in proof.pending]
    if failing:
        nodes = list(nodes) + [node.id for node in proof.failing]
    nodes = unique(nodes)

    res_lines = []

    start_server = options.port is None

    kore_rpc_command = None
    if isinstance(options.kore_rpc_command, str):
        kore_rpc_command = options.kore_rpc_command.split()

    with legacy_explore(
        foundry.kevm,
        kcfg_semantics=KEVMSemantics(),
        id=proof.id,
        bug_report=options.bug_report,
        kore_rpc_command=kore_rpc_command,
        llvm_definition_dir=foundry.llvm_library if options.use_booster else None,
        smt_timeout=options.smt_timeout,
        smt_retry_limit=options.smt_retry_limit,
        smt_tactic=options.smt_tactic,
        log_succ_rewrites=options.log_succ_rewrites,
        log_fail_rewrites=options.log_fail_rewrites,
        start_server=start_server,
        port=options.port,
        maude_port=options.maude_port,
    ) as kcfg_explore:
        for node_id in nodes:
            res_lines.append('')
            res_lines.append(f'Node id: {node_id}')
            node = proof.kcfg.node(node_id)
            res_lines.extend(print_model(node, kcfg_explore))

    return '\n'.join(res_lines)


def read_recorded_state_diff(state_file: Path) -> list[StateDiffEntry]:
    if not state_file.exists():
        raise FileNotFoundError(f'Account accesses dictionary file not found: {state_file}')
    accesses = json.loads(state_file.read_text())['accountAccesses']
    return [StateDiffEntry(_a) for _a in accesses]


def read_recorded_state_dump(state_file: Path) -> list[StateDumpEntry]:
    if not state_file.exists():
        raise FileNotFoundError(f'Account accesses dictionary file not found: {state_file}')
    accounts = json.loads(state_file.read_text())
    return [StateDumpEntry(account, accounts[account]) for account in list(accounts)]


def read_contract_names(contract_names: Path) -> dict[str, str]:
    if not contract_names.exists():
        raise FileNotFoundError(f'Contract names dictionary file not found: {contract_names}')
    return json.loads(contract_names.read_text())


class FoundryNodePrinter(KEVMNodePrinter):
    foundry: Foundry
    contract_name: str
    omit_unstable_output: bool

    def __init__(self, foundry: Foundry, contract_name: str, omit_unstable_output: bool = False):
        KEVMNodePrinter.__init__(self, foundry.kevm)
        self.foundry = foundry
        self.contract_name = contract_name
        self.omit_unstable_output = omit_unstable_output

    def print_node(self, kcfg: KCFG, node: KCFG.Node) -> list[str]:
        ret_strs = super().print_node(kcfg, node)
        _pc = node.cterm.try_cell('PC_CELL')
        if type(_pc) is KToken and _pc.sort == INT:
            srcmap_data = self.foundry.srcmap_data(self.contract_name, int(_pc.token))
            if not self.omit_unstable_output and srcmap_data is not None:
                path, start, end = srcmap_data
                ret_strs.append(f'src: {str(path)}:{start}:{end}')

        calldata_cell = node.cterm.try_cell('CALLDATA_CELL')
        program_cell = node.cterm.try_cell('PROGRAM_CELL')

        if type(program_cell) is KToken:
            selector_bytes = None
            if type(calldata_cell) is KToken:
                selector_bytes = ast.literal_eval(calldata_cell.token)
                selector_bytes = selector_bytes[:4]
            elif (
                type(calldata_cell) is KApply and calldata_cell.label.name == '_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes'
            ):
                first_bytes = flatten_label(label='_+Bytes__BYTES-HOOKED_Bytes_Bytes_Bytes', kast=calldata_cell)[0]
                if type(first_bytes) is KToken:
                    selector_bytes = ast.literal_eval(first_bytes.token)
                    selector_bytes = selector_bytes[:4]

            if selector_bytes is not None:
                selector = int.from_bytes(selector_bytes, 'big')
                current_contract_name = self.foundry.contract_name_from_bytecode(ast.literal_eval(program_cell.token))
                for contract_name, contract_obj in self.foundry.contracts.items():
                    if current_contract_name == contract_name:
                        for method in contract_obj.methods:
                            if method.id == selector:
                                ret_strs.append(f'method: {method.qualified_name}')

        return ret_strs


class FoundryAPRNodePrinter(FoundryNodePrinter, APRProofNodePrinter):
    def __init__(self, foundry: Foundry, contract_name: str, proof: APRProof, omit_unstable_output: bool = False):
        FoundryNodePrinter.__init__(self, foundry, contract_name, omit_unstable_output=omit_unstable_output)
        APRProofNodePrinter.__init__(self, proof, foundry.kevm)


def foundry_node_printer(
    foundry: Foundry, contract_name: str, proof: APRProof, omit_unstable_output: bool = False
) -> NodePrinter:
    if type(proof) is APRProof:
        return FoundryAPRNodePrinter(foundry, contract_name, proof, omit_unstable_output=omit_unstable_output)
    raise ValueError(f'Cannot build NodePrinter for proof type: {type(proof)}')


def init_project(project_root: Path, *, skip_forge: bool) -> None:
    """
    Wrapper around `forge init` that creates new Foundry projects compatible with Kontrol.

    :param skip_forge: Skip the `forge init` process, if there already exists a Foundry project.
    :param project_root: Name of the new project that is created.
    """

    if not skip_forge:
        run_process_2(['forge', 'init', str(project_root), '--no-git'], logger=_LOGGER)

    root = ensure_dir_path(project_root)
    write_to_file(root / 'lemmas.k', empty_lemmas_file_contents())
    write_to_file(root / 'KONTROL.md', kontrol_file_contents())
    write_to_file(root / 'kontrol.toml', kontrol_toml_file_contents())
    append_to_file(root / 'foundry.toml', foundry_toml_extra_contents())
    run_process_2(
        ['forge', 'install', '--no-git', 'runtimeverification/kontrol-cheatcodes'],
        logger=_LOGGER,
        cwd=root,
    )


def foundry_clean(foundry: Foundry, options: CleanOptions) -> None:
    if options.proofs and options.old_proofs:
        raise AttributeError('Use --proofs or --old-proofs, but not both!')
    if options.proofs:
        foundry.remove_proofs_dir()
    elif options.old_proofs:
        foundry.remove_old_proofs()
    else:
        run_process_2(['forge', 'clean', '--root', str(options.foundry_root)], logger=_LOGGER)
