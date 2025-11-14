from __future__ import annotations

import ast
import datetime
import json
import logging
import os
import re
import shutil
import traceback
import xml.etree.ElementTree as Et
from functools import cached_property
from os import listdir
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import tomlkit
from eth_abi import decode, encode
from kevm_pyk.kevm import KEVM, CustomStep, KEVMSemantics
from kevm_pyk.utils import legacy_explore, print_model
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KInner, KSequence, KSort, KToken, KVariable, Subst
from pyk.kast.manip import (
    cell_label_to_var_name,
    free_vars,
    minimize_term,
    set_cell,
    top_down,
)
from pyk.kast.outer import KRule
from pyk.kast.prelude.bytes import bytesToken
from pyk.kast.prelude.collections import map_empty
from pyk.kast.prelude.k import DOTS, GENERATED_TOP_CELL
from pyk.kast.prelude.kbool import notBool
from pyk.kast.prelude.kint import INT, intToken
from pyk.kast.prelude.ml import mlEqualsFalse, mlEqualsTrue
from pyk.kcfg.kcfg import Step
from pyk.kdist import kdist
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.utils import ensure_dir_path, hash_str, run_process, run_process_2, single, unique

from . import VERSION
from .solc_to_k import Contract, _contract_name_from_bytecode
from .storage_generation import generate_setup_contract
from .utils import (
    _read_digest_file,
    decode_log_message,
    empty_lemmas_file_contents,
    ensure_name_is_unique,
    kontrol_file_contents,
    kontrol_test_file_contents,
    kontrol_toml_file_contents,
    kontrol_up_to_date,
    write_to_file,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, Final

    from pyk.cterm import CTermSymbolic
    from pyk.kast.outer import KAst, KFlatModule
    from pyk.kcfg import KCFG
    from pyk.kcfg.kcfg import NodeIdLike
    from pyk.kcfg.semantics import KCFGExtendResult
    from pyk.proof.implies import RefutationProof
    from pyk.utils import BugReport

    from .options import (
        CleanOptions,
        GetModelOptions,
        MergeNodesOptions,
        MinimizeProofOptions,
        RefuteNodeOptions,
        RemoveNodeOptions,
        SectionEdgeOptions,
        SetupStorageOptions,
        SimplifyNodeOptions,
        SplitNodeOptions,
        StepNodeOptions,
        UnrefuteNodeOptions,
    )

_LOGGER: Final = logging.getLogger(__name__)


class KontrolSemantics(KEVMSemantics):

    allow_ffi_calls: bool

    def __init__(
        self, auto_abstract_gas: bool = False, allow_symbolic_program: bool = False, allow_ffi_calls: bool = False
    ) -> None:
        self.allow_ffi_calls = allow_ffi_calls

        custom_steps = (
            CustomStep(self._ffi_pattern, self._exec_ffi_custom_step),
            CustomStep(self._rename_pattern, self._exec_rename_custom_step),
            CustomStep(self._forget_branch_pattern, self._exec_forget_custom_step),
            CustomStep(self._console_log_pattern, self._exec_console_log_custom_step),
        )

        super().__init__(
            auto_abstract_gas=auto_abstract_gas,
            allow_symbolic_program=allow_symbolic_program,
            custom_step_definitions=custom_steps,
        )

    @staticmethod
    def cut_point_rules(
        break_on_jumpi: bool,
        break_on_jump: bool,
        break_on_calls: bool,
        break_on_storage: bool,
        break_on_basic_blocks: bool,
        break_on_load_program: bool,
    ) -> list[str]:
        return [
            'FOUNDRY-CHEAT-CODES.rename',
            'FOUNDRY-CHEAT-CODES.cheatcode.call.ffi',
            'FOUNDRY-ACCOUNTS.forget',
        ] + KEVMSemantics.cut_point_rules(
            break_on_jumpi,
            break_on_jump,
            break_on_calls,
            break_on_storage,
            break_on_basic_blocks,
            break_on_load_program,
        )

    @property
    def _rename_pattern(self) -> KSequence:
        return KSequence(
            [
                KApply('foundry_rename', [KVariable('###RENAME_TARGET'), KVariable('###NEW_NAME')]),
                KVariable('###CONTINUATION'),
            ]
        )

    @property
    def _forget_branch_pattern(self) -> KSequence:
        return KSequence(
            [
                KApply('cheatcode_forget', [KVariable('###TERM1'), KVariable('###OPERATOR'), KVariable('###TERM2')]),
                KVariable('###CONTINUATION'),
            ]
        )

    @property
    def _console_log_pattern(self) -> KSequence:
        return KSequence(
            [KApply('console_log', [KVariable('###SELECTOR'), KVariable('###DATA')]), KVariable('###CONTINUATION')]
        )

    @property
    def _ffi_pattern(self) -> KSequence:
        return KSequence([KApply('ffi_shell', KVariable('###CMD')), KVariable('###CONTINUATION')])

    def _exec_rename_custom_step(self, subst: Subst, cterm: CTerm, _c: CTermSymbolic) -> KCFGExtendResult | None:
        # Extract the target var and new name from the substitution
        target_var = subst['###RENAME_TARGET']
        name_token = subst['###NEW_NAME']
        assert type(target_var) is KVariable
        assert type(name_token) is KToken

        # Ensure the name is unique
        name_str = name_token.token[1:-1]
        if len(name_str) == 0:
            _LOGGER.warning('Name of symbolic variable cannot be empty. Reverting to the default name.')
            return None
        name = ensure_name_is_unique(name_str, cterm)

        # Replace var in configuration and constraints
        rename_subst = Subst({target_var.name: KVariable(name, target_var.sort)})
        config = rename_subst(cterm.config)
        constraints = [rename_subst(constraint) for constraint in cterm.constraints]
        new_cterm = CTerm.from_kast(set_cell(config, 'K_CELL', KSequence(subst['###CONTINUATION'])))

        _LOGGER.info(f'Renaming {target_var.name} to {name}')
        return Step(CTerm(new_cterm.config, constraints), 1, (), ['foundry_rename'], cut=True)

    def _exec_forget_custom_step(
        self, subst: Subst, cterm: CTerm, cterm_symbolic: CTermSymbolic
    ) -> KCFGExtendResult | None:
        """Remove the constraint at the top of K_CELL of a given CTerm from its path constraints,
           as part of the 'FOUNDRY-ACCOUNTS.forget' cut-rule.
        :param cterm: CTerm representing a proof node
        :param cterm_symbolic: CTermSymbolic instance
        :return: A Step of depth 1 carrying a new configuration in which the constraint is consumed from the top
                 of the K cell and is removed from the initial path constraints if it existed, together with
                 information that the `cheatcode_forget` rule has been applied.
        """

        def _find_constraints_to_keep(cterm: CTerm, constraint_vars: frozenset[str]) -> set[KInner]:
            range_patterns: list[KInner] = [
                mlEqualsTrue(KApply('_<Int_', KVariable('###VARL', INT), KVariable('###VARR', INT))),
                mlEqualsTrue(KApply('_<=Int_', KVariable('###VARL', INT), KVariable('###VARR', INT))),
                mlEqualsTrue(notBool(KApply('_==Int_', KVariable('###VARL', INT), KVariable('###VARR', INT)))),
            ]
            constraints_to_keep: set[KInner] = set()
            for constraint in cterm.constraints:
                for pattern in range_patterns:
                    subst_rcp = pattern.match(constraint)
                    if subst_rcp is not None and (
                        (
                            type(subst_rcp['###VARL']) is KVariable
                            and subst_rcp['###VARL'].name in constraint_vars
                            and type(subst_rcp['###VARR']) is KToken
                        )
                        or (
                            type(subst_rcp['###VARR']) is KVariable
                            and subst_rcp['###VARR'].name in constraint_vars
                            and type(subst_rcp['###VARL']) is KToken
                        )
                    ):
                        constraints_to_keep.add(constraint)
                        break
            return constraints_to_keep

        def _filter_constraints_by_simplification(
            cterm_symbolic: CTermSymbolic,
            initial_cterm: CTerm,
            constraints_to_remove: list[KInner],
            constraints_to_keep: set[KInner],
            constraints: set[KInner],
            empty_config: CTerm,
        ) -> set[KInner]:
            for constraint_variant in constraints_to_remove:
                simplification_cterm = initial_cterm.add_constraint(constraint_variant)
                result_cterm, _ = cterm_symbolic.simplify(simplification_cterm)
                # Extract constraints that appear after simplification but are not in the 'to keep' set
                result_constraints = set(result_cterm.constraints).difference(constraints_to_keep)

                if len(result_constraints) == 1:
                    target_constraint = single(result_constraints)
                    if target_constraint in constraints:
                        _LOGGER.info(f'forgetBranch: removing constraint: {target_constraint}')
                        constraints.remove(target_constraint)
                        break
                    else:
                        _LOGGER.info(f'forgetBranch: constraint: {target_constraint} not found in current constraints')
                else:
                    # If no constraints or multiple constraints appear, log this scenario.
                    if len(result_constraints) == 0:
                        _LOGGER.info(f'forgetBranch: constraint {constraint_variant} entailed by remaining constraints')
                        result_cterm, _ = cterm_symbolic.simplify(CTerm(empty_config.config, [constraint_variant]))
                        if len(result_cterm.constraints) == 1:
                            to_remove = single(result_cterm.constraints)
                            if to_remove in constraints:
                                _LOGGER.info(f'forgetBranch: removing constraint: {to_remove}')
                                constraints.remove(to_remove)
                    else:
                        _LOGGER.info(
                            f'forgetBranch: more than one constraint found after simplification and removal:\n{result_constraints}'
                        )
            return constraints

        _operators = ['_==Int_', '_=/=Int_', '_<=Int_', '_<Int_', '_>=Int_', '_>Int_']

        # Extract the terms and operator from the substitution
        fst_term = subst['###TERM1']
        snd_term = subst['###TERM2']
        operator = subst['###OPERATOR']
        assert isinstance(operator, KToken)
        # Construct the positive and negative constraints
        pos_constraint = mlEqualsTrue(KApply(_operators[int(operator.token)], fst_term, snd_term))
        neg_constraint = mlEqualsTrue(notBool(KApply(_operators[int(operator.token)], fst_term, snd_term)))
        # To be able to better simplify, we maintain range constraints on the variables present in the constraint
        constraint_vars: frozenset[str] = free_vars(fst_term).union(free_vars(snd_term))
        constraints_to_keep: set[KInner] = _find_constraints_to_keep(cterm, constraint_vars)

        # Set up initial configuration for constraint simplification, and simplify it to get all
        # of the kept constraints in the form in which they will appear after constraint simplification
        kevm = KEVM(kdist.get('kontrol.base'))
        empty_config: CTerm = CTerm.from_kast(kevm.definition.empty_config(GENERATED_TOP_CELL))
        initial_cterm, _ = cterm_symbolic.simplify(CTerm(empty_config.config, constraints_to_keep))
        constraints_to_keep = set(initial_cterm.constraints)

        # Simplify in the presence of constraints to keep, then remove the constraints to keep to
        # reveal simplified constraint, then remove if present in original constraints
        new_constraints: set[KInner] = _filter_constraints_by_simplification(
            cterm_symbolic=cterm_symbolic,
            initial_cterm=initial_cterm,
            constraints_to_remove=[pos_constraint, neg_constraint],
            constraints_to_keep=constraints_to_keep,
            constraints=set(cterm.constraints),
            empty_config=empty_config,
        )

        # Update the K_CELL with the continuation
        new_cterm = CTerm.from_kast(set_cell(cterm.kast, 'K_CELL', KSequence(subst['###CONTINUATION'])))
        return Step(CTerm(new_cterm.config, new_constraints), 1, (), ['cheatcode_forget'], cut=True)

    def _exec_console_log_custom_step(self, subst: Subst, cterm: CTerm, _c: CTermSymbolic) -> KCFGExtendResult | None:
        selector_token = subst['###SELECTOR']
        data = subst['###DATA']
        assert type(selector_token) is KToken

        try:
            if type(data) is KToken:
                selector = int(selector_token.token)
                output = decode_log_message(data.token, selector)
                if output is not None:
                    print(f'    {output}')
            else:
                kevm = KEVM(kdist.get('kontrol.base'))
                print(f'    {kevm.pretty_print(data)}')
        except Exception as e:
            _LOGGER.warning(f'Console log decode error: {e}')

        # Update the K_CELL with the continuation
        new_cterm = CTerm.from_kast(set_cell(cterm.kast, 'K_CELL', KSequence(subst['###CONTINUATION'])))
        return Step(CTerm(new_cterm.config, cterm.constraints), 1, (), ['console.log'], cut=True)

    def _exec_ffi_custom_step(self, subst: Subst, cterm: CTerm, _c: CTermSymbolic) -> KCFGExtendResult | None:
        """Execute vm.ffi() cheatcode by running external commands and encoding their output as ABI bytes.

        This function decodes the command from the ABI-encoded string array, executes it as a subprocess, and processes
        the stdout. If stdout is valid hex (with or without '0x' prefix), it decodes the hex to bytes; otherwise it
        treats stdout as raw bytes. The result is ABI-encoded as dynamic bytes type and placed in the OUTPUT_CELL.
        If the command fails (non-zero exit code), the execution halts with EVMC_REVERT status.

        :param subst: Substitution containing the values obtained by matching the `self._ffi_pattern`.
        :param cterm: Current configuration term representing the EVM state.
        :param _c: Symbolic configuration term (unused).
        :return: None if FFI is disabled. Otherwise, Step with OUTPUT_CELL set to ABI-encoded result and updated K_CELL
                continuation, tagged with 'kontrol.ffi.success'. On command failure, returns Step with EVMC_REVERT
                status tagged with 'kontrol.ffi.failure'.
        """
        if not self.allow_ffi_calls:
            _LOGGER.warning(
                'ffi calls disabled, vm.ffi() will return a fresh symbolic value. To overwrite this, use --ffi.'
            )
            return None

        cmd = subst['###CMD']
        assert type(cmd) is KToken

        # Decode ABI string[]
        data = ast.literal_eval(cmd.token)
        cmd_decoded = decode(['string[]'], data)[0]

        # Execute command
        process_result = run_process(
            cmd_decoded,
            check=False,  # Don't raise on non-zero exit
            pipe_stdout=True,
            pipe_stderr=True,
            cwd=Path.cwd(),
            logger=_LOGGER,
        )

        # If the process failed, halt the execution and change the status code to EVMC_REVERT
        if process_result.returncode != 0:
            _LOGGER.info(f'ffi command failed: {cmd_decoded}')
            new_cterm = CTerm.from_kast(
                set_cell(
                    cterm.kast,
                    'K_CELL',
                    KSequence([KApply('end', KApply('EVMC_REVERT')), subst['###CONTINUATION']]),
                )
            )
            return Step(CTerm(new_cterm.config, cterm.constraints), 1, (), ['kontrol.ffi.failure'], cut=True)

        # Parse stdout
        stdout = process_result.stdout.strip()

        try:
            # Try decode as hex (with or without 0x prefix)
            hex_str = stdout[2:] if stdout.startswith('0x') else stdout
            raw_bytes = bytes.fromhex(hex_str)
        except ValueError:
            # Not hex, treat as raw bytes
            raw_bytes = stdout.encode()

        # ABI-encode as bytes (dynamic type)
        encoded_output = encode(['bytes'], [raw_bytes])

        # Update cells
        new_cterm = CTerm.from_kast(set_cell(cterm.kast, 'OUTPUT_CELL', bytesToken(encoded_output)))
        new_cterm = CTerm.from_kast(set_cell(new_cterm.kast, 'K_CELL', KSequence(subst['###CONTINUATION'])))

        return Step(CTerm(new_cterm.config, cterm.constraints), 1, (), ['kontrol.ffi.success'], cut=True)


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

        current_profile = self._toml['profile'].get(profile_name, {})
        default_profile = self._toml['profile'].get('default', {})

        return {**default_profile, **current_profile}

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
    def build_info(self) -> Path:
        build_info_path = self.profile.get('build_info_path')

        if build_info_path:
            return self._root / build_info_path
        else:
            return self.out / 'build-info'

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

    def build(self, metadata: bool) -> None:
        forge_build_args = [
            'forge',
            'build',
            '--build-info',
            '--extra-output',
            'storageLayout',
            'evm.bytecode.generatedSources',
            'evm.deployedBytecode.generatedSources',
            '--root',
            str(self._root),
        ] + (['--no-metadata'] if not metadata else [])
        try:
            run_process_2(
                forge_build_args,
                logger=_LOGGER,
            )
        except FileNotFoundError as err:
            raise RuntimeError(
                "Error: 'forge' command not found. Please ensure that 'forge' is installed and added to your PATH."
            ) from err
        except CalledProcessError as err:
            raise RuntimeError(f"Couldn't forge build! {err.stderr.strip()}") from err

    def load_lemmas(self, lemmas_id: str | None) -> KFlatModule | None:
        if lemmas_id is None:
            return None
        lemmas_file, lemmas_name, *_ = lemmas_id.split(':')
        lemmas_path = Path(lemmas_file)
        if not lemmas_path.is_file():
            raise ValueError(f'Supplied lemmas path is not a file: {lemmas_path}')
        modules = self.kevm.parse_modules(
            lemmas_path, module_name=lemmas_name, include_dirs=(kdist.get('kontrol.base'),)
        )
        lemmas_module = single(module for module in modules.modules if module.name == lemmas_name)
        non_rule_sentences = [sent for sent in lemmas_module.sentences if not isinstance(sent, KRule)]
        if non_rule_sentences:
            raise ValueError(f'Supplied lemmas module contains non-Rule sentences: {non_rule_sentences}')
        return lemmas_module

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

    @staticmethod
    def hevm_success(s: KInner, dst: KInner, out: KInner) -> KApply:
        return KApply('hevm_success', [s, dst, out])

    @staticmethod
    def hevm_fail(s: KInner, dst: KInner) -> KApply:
        return KApply('hevm_fail', [s, dst])

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

    @staticmethod
    def address_DEFAULT_CALLER() -> KToken:  # noqa: N802
        return intToken(0x1804C8AB1F12E6BBF3894D4083F33E07309D1F38)

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


def foundry_to_xml(foundry: Foundry, proofs: list[APRProof], report_name: str) -> None:
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
    tree.write(report_name)


def foundry_minimize_proof(foundry: Foundry, options: MinimizeProofOptions) -> None:
    test_id = foundry.get_test_id(options.test, options.version)
    apr_proof = foundry.get_apr_proof(test_id)
    apr_proof.minimize_kcfg(heuristics=KontrolSemantics(), merge=options.merge)
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
    parsed_condition = foundry.kevm.parse_token(token, as_rule=True)

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
        kcfg_semantics=KontrolSemantics(),
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
        extra_module=foundry.load_lemmas(options.lemmas),
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
        if not all(KontrolSemantics().same_loop(nodes[0].cterm, nd.cterm) for nd in nodes):
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
        kcfg_semantics=KontrolSemantics(),
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
        extra_module=foundry.load_lemmas(options.lemmas),
    ) as kcfg_explore:
        node = options.node
        for _i in range(options.repeat):
            node = kcfg_explore.step(apr_proof.kcfg, node, apr_proof.logs, depth=options.depth)
            apr_proof.write_proof_data()


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
        kcfg_semantics=KontrolSemantics(),
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
        extra_module=foundry.load_lemmas(options.lemmas),
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
        kcfg_semantics=KontrolSemantics(),
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
        extra_module=foundry.load_lemmas(options.lemmas),
    ) as kcfg_explore:
        for node_id in nodes:
            res_lines.append('')
            res_lines.append(f'Node id: {node_id}')
            node = proof.kcfg.node(node_id)
            res_lines.extend(print_model(node, kcfg_explore))

    return '\n'.join(res_lines)


def init_project(project_root: Path, *, skip_forge: bool, skip_kontrol_test: bool = False) -> None:
    """
    Wrapper around `forge init` that creates new Foundry projects compatible with Kontrol.

    :param skip_forge: Skip the `forge init` process, if there already exists a Foundry project.
    :param project_root: Name of the new project that is created.
    :param skip_kontrol_test: Skip generating KontrolTest.sol file.
    """

    if not skip_forge:
        run_process_2(['forge', 'init', str(project_root), '--no-git'], logger=_LOGGER)

    root = ensure_dir_path(project_root)
    write_to_file(root / 'lemmas.k', empty_lemmas_file_contents())
    write_to_file(root / 'KONTROL.md', kontrol_file_contents())
    write_to_file(root / 'kontrol.toml', kontrol_toml_file_contents())

    if not skip_kontrol_test:
        kontrol_test_dir = ensure_dir_path(root / 'test' / 'kontrol')
        write_to_file(kontrol_test_dir / 'KontrolTest.sol', kontrol_test_file_contents())

    try:
        run_process_2(
            ['forge', 'install', '--no-git', 'runtimeverification/kontrol-cheatcodes'],
            logger=_LOGGER,
            cwd=root,
        )
    except CalledProcessError as e:
        # If `kontrol-cheatcodes` is already installed, continue
        if 'already exists' in e.stderr.lower():
            _LOGGER.info('kontrol-cheatcodes already installed, skipping installation')
        else:
            raise


def foundry_storage_generation(foundry: Foundry, options: SetupStorageOptions) -> None:
    """Generate storage constants for given contracts."""
    from .storage_generation import (
        generate_storage_constants,
        get_storage_layout_from_foundry,
    )

    _LOGGER.info(f'Starting storage generation for contracts: {", ".join(options.contract_names)}')

    # Run kontrol init with skip_forge=True to ensure KontrolTest.sol is available (unless skipped)
    if not options.skip_kontrol_init:
        _LOGGER.info('Running kontrol init with skip_forge=True to ensure KontrolTest.sol is available')
        init_project(project_root=foundry._root, skip_forge=True)

    # Build the project first to ensure storage layout is available
    _LOGGER.info('Building Foundry project to ensure storage layout is available')
    foundry.build(metadata=True)

    # Process each contract
    generated_files = []
    for contract_name in options.contract_names:
        _LOGGER.info(f'Processing contract: {contract_name}')

        # Get storage layout from Foundry object
        contract_name, storage, types = get_storage_layout_from_foundry(foundry, contract_name)

        # Generate storage constants
        storage_constants = generate_storage_constants(contract_name, options.solidity_version, storage, types)

        # Determine output file path
        if options.output_file:
            # If output_file is specified, use it as a directory and append contract name
            output_dir = Path(options.output_file)
            output_path = output_dir / f'{contract_name}StorageConstants.sol'
        else:
            output_path = foundry._root / 'test' / 'kontrol' / 'storage' / f'{contract_name}StorageConstants.sol'

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write storage constants file
        with open(output_path, 'w') as f:
            f.write(storage_constants)

        generated_files.append(output_path)
        _LOGGER.info(f'Generated storage constants file: {output_path}')

        # Generate setup contract if requested
        if options.generate_setup_contracts:
            setup_contract = generate_setup_contract(contract_name, options.solidity_version, storage, types)

            # Determine setup contract output path
            if options.output_file:
                setup_output_path = output_dir / f'{contract_name}StorageSetup.sol'
            else:
                setup_output_path = foundry._root / 'test' / 'kontrol' / 'setup' / f'{contract_name}StorageSetup.sol'

            # Ensure setup directory exists
            setup_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write setup contract file
            with open(setup_output_path, 'w') as f:
                f.write(setup_contract)

            generated_files.append(setup_output_path)
            _LOGGER.info(f'Generated setup contract file: {setup_output_path}')

    _LOGGER.info(
        f'Storage generation completed successfully! Generated {len(generated_files)} files: {[str(f) for f in generated_files]}'
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
