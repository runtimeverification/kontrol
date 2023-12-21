from __future__ import annotations

import json
import logging
import os
import re
import sys
from functools import cached_property
from os import listdir
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import tomlkit
from kevm_pyk.kevm import KEVM, KEVMNodePrinter, KEVMSemantics
from kevm_pyk.utils import byte_offset_to_lines, legacy_explore, print_failure_info, print_model
from pyk.kast.inner import KApply, KSort, KToken
from pyk.kast.manip import minimize_term
from pyk.kcfg import KCFG
from pyk.prelude.bytes import bytesToken
from pyk.prelude.kbool import notBool
from pyk.prelude.kint import INT, intToken
from pyk.proof.proof import Proof
from pyk.proof.reachability import APRBMCProof, APRProof
from pyk.proof.show import APRBMCProofNodePrinter, APRProofNodePrinter, APRProofShow
from pyk.utils import ensure_dir_path, hash_str, run_process, single, unique

from .deployment import DeploymentSummary
from .solc_to_k import Contract

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, Final

    from pyk.cterm import CTerm
    from pyk.kast.inner import KInner
    from pyk.kcfg.kcfg import NodeIdLike
    from pyk.kcfg.tui import KCFGElem
    from pyk.proof.show import NodePrinter
    from pyk.utils import BugReport

    from .options import RPCOptions


_LOGGER: Final = logging.getLogger(__name__)


class Foundry:
    _root: Path
    _toml: dict[str, Any]
    _bug_report: BugReport | None

    class Sorts:
        FOUNDRY_CELL: Final = KSort('FoundryCell')

    def __init__(
        self,
        foundry_root: Path,
        bug_report: BugReport | None = None,
    ) -> None:
        self._root = foundry_root
        with (foundry_root / 'foundry.toml').open('rb') as f:
            self._toml = tomlkit.load(f)
        self._bug_report = bug_report

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
        return KEVM(
            definition_dir=self.kompiled,
            main_file=self.main_file,
            use_directory=use_directory,
            bug_report=self._bug_report,
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
            _LOGGER.debug(f'Processing contract file: {json_path}')
            contract_name = json_path.split('/')[-1]
            contract_json = json.loads(Path(json_path).read_text())
            contract_name = contract_name[0:-5] if contract_name.endswith('.json') else contract_name
            contract = Contract(contract_name, contract_json, foundry=True)

            _contracts[contract.name_with_path] = contract

        return _contracts

    def mk_proofs_dir(self) -> None:
        self.proofs_dir.mkdir(exist_ok=True)

    def method_digest(self, contract_name: str, method_sig: str) -> str:
        return self.contracts[contract_name].method_by_sig[method_sig].digest

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
        digest_dict = json.loads(self.digest_file.read_text())
        if 'foundry' not in digest_dict:
            digest_dict['foundry'] = ''
        self.digest_file.write_text(json.dumps(digest_dict, indent=4))
        return digest_dict['foundry'] == self.digest

    def update_digest(self) -> None:
        digest_dict = {}
        if self.digest_file.exists():
            digest_dict = json.loads(self.digest_file.read_text())
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
        return ['NO DATA']

    def build(self) -> None:
        try:
            run_process(['forge', 'build', '--root', str(self._root)], logger=_LOGGER)
        except FileNotFoundError:
            print("Error: 'forge' command not found. Please ensure that 'forge' is installed and added to your PATH.")
            sys.exit(1)
        except CalledProcessError as err:
            raise RuntimeError("Couldn't forge build!") from err

    @cached_property
    def all_tests(self) -> list[str]:
        return [
            f'{contract.name_with_path}.{method.signature}'
            for contract in self.contracts.values()
            if contract.name_with_path.endswith('Test')
            for method in contract.methods
            if method.name.startswith('test')
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

    def matching_tests(self, tests: list[str]) -> list[str]:
        all_tests = self.all_tests
        all_non_tests = self.all_non_tests
        tests = self._escape_brackets(tests)
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

    def matching_sigs(self, test: str) -> list[str]:
        test_sigs = self.matching_tests([test])
        return test_sigs

    def get_test_id(self, test: str, id: int | None) -> str:
        matching_proofs = self.proofs_with_test(test)
        if not matching_proofs:
            raise ValueError(f'Found no matching proofs for {test}.')
        if id is None:
            if len(matching_proofs) > 1:
                raise ValueError(
                    f'Found {len(matching_proofs)} matching proofs for {test}. Use the --version flag to choose one.'
                )
            test_id = single(matching_proofs).id
            return test_id
        else:
            for proof in matching_proofs:
                if proof.id.endswith(str(id)):
                    return proof.id
            raise ValueError('No proof matching this predicate.')

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
                    KApply('FoundryCheat_FOUNDRY-ACCOUNTS_FoundryContract'),
                    KApply('Failed_FOUNDRY-ACCOUNTS_FoundryField'),
                ],
            )
        )

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
            KApply('.Map'),
            intToken(0),
        )

    @staticmethod
    def help_info() -> list[str]:
        res_lines: list[str] = []
        print_foundry_success_info = any('foundry_success' in line for line in res_lines)
        if print_foundry_success_info:
            res_lines.append('')
            res_lines.append('See `foundry_success` predicate for more information:')
            res_lines.append(
                'https://github.com/runtimeverification/kontrol/blob/master/src/kontrol/kdist/foundry.md#foundry-success-predicate'
            )
        res_lines.append('')
        res_lines.append(
            'Access documentation for KEVM foundry integration at https://docs.runtimeverification.com/kontrol'
        )
        return res_lines

    def proofs_with_test(self, test: str) -> list[Proof]:
        proofs = [
            self.get_optional_proof(pid)
            for pid in listdir(self.proofs_dir)
            if re.search(single(self._escape_brackets([test])), pid.split(':')[0])
        ]
        return [proof for proof in proofs if proof is not None]

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

        if user_specified_version:
            _LOGGER.info(f'Using user-specified version {user_specified_version} for test {test}')
            if not Proof.proof_data_exists(f'{test}:{user_specified_version}', self.proofs_dir):
                raise ValueError(f'The specified version {user_specified_version} of proof {test} does not exist.')
            if not method.up_to_date(self.digest_file):
                _LOGGER.warn(
                    f'Using specified version {user_specified_version} of proof {test}, but it is out of date.'
                )
            return user_specified_version

        if not method.up_to_date(self.digest_file):
            _LOGGER.info(f'Creating a new version of test {test} because it is out of date.')
            return self.free_proof_version(test)

        latest_version = self.latest_proof_version(test)
        if latest_version is not None:
            _LOGGER.info(
                f'Using the the latest version {latest_version} of test {test} because it is up to date and no version was specified.'
            )
            if type(method) is Contract.Method and not method.contract_up_to_date(self.digest_file):
                _LOGGER.warning(
                    f'Test {test} was not reinitialized because it is up to date, but the contract it is a part of has changed.'
                )
            return latest_version

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
        proof_ids = listdir(self.proofs_dir)
        versions = {int(pid.split(':')[1]) for pid in proof_ids if pid.split(':')[0] == test}
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


def foundry_show(
    foundry: Foundry,
    test: str,
    version: int | None = None,
    nodes: Iterable[NodeIdLike] = (),
    node_deltas: Iterable[tuple[NodeIdLike, NodeIdLike]] = (),
    to_module: bool = False,
    minimize: bool = True,
    sort_collections: bool = False,
    omit_unstable_output: bool = False,
    pending: bool = False,
    failing: bool = False,
    failure_info: bool = False,
    counterexample_info: bool = False,
    smt_timeout: int | None = None,
    smt_retry_limit: int | None = None,
    port: int | None = None,
    maude_port: int | None = None,
) -> str:
    contract_name, _ = single(foundry.matching_tests([test])).split('.')
    test_id = foundry.get_test_id(test, version)
    proof = foundry.get_apr_proof(test_id)

    if pending:
        nodes = list(nodes) + [node.id for node in proof.pending]
    if failing:
        nodes = list(nodes) + [node.id for node in proof.failing]
    nodes = unique(nodes)

    unstable_cells = [
        '<program>',
        '<jumpDests>',
        '<pc>',
        '<gas>',
        '<code>',
    ]

    node_printer = foundry_node_printer(foundry, contract_name, proof)
    proof_show = APRProofShow(foundry.kevm, node_printer=node_printer)

    res_lines = proof_show.show(
        proof,
        nodes=nodes,
        node_deltas=node_deltas,
        to_module=to_module,
        minimize=minimize,
        sort_collections=sort_collections,
        omit_cells=(unstable_cells if omit_unstable_output else []),
    )

    start_server = port is None

    if failure_info:
        with legacy_explore(
            foundry.kevm,
            kcfg_semantics=KEVMSemantics(),
            id=test_id,
            smt_timeout=smt_timeout,
            smt_retry_limit=smt_retry_limit,
            start_server=start_server,
            port=port,
            maude_port=maude_port,
        ) as kcfg_explore:
            res_lines += print_failure_info(proof, kcfg_explore, counterexample_info)
            res_lines += Foundry.help_info()

    return '\n'.join(res_lines)


def foundry_to_dot(foundry: Foundry, test: str, version: int | None = None) -> None:
    dump_dir = foundry.proofs_dir / 'dump'
    test_id = foundry.get_test_id(test, version)
    contract_name, _ = single(foundry.matching_tests([test])).split('.')
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


def foundry_remove_node(foundry: Foundry, test: str, node: NodeIdLike, version: int | None = None) -> None:
    test_id = foundry.get_test_id(test, version)
    apr_proof = foundry.get_apr_proof(test_id)
    node_ids = apr_proof.prune(node)
    _LOGGER.info(f'Pruned nodes: {node_ids}')
    apr_proof.write_proof_data()


def foundry_simplify_node(
    foundry: Foundry,
    test: str,
    node: NodeIdLike,
    rpc_options: RPCOptions,
    version: int | None = None,
    replace: bool = False,
    minimize: bool = True,
    sort_collections: bool = False,
    bug_report: BugReport | None = None,
) -> str:
    test_id = foundry.get_test_id(test, version)
    apr_proof = foundry.get_apr_proof(test_id)
    cterm = apr_proof.kcfg.node(node).cterm
    start_server = rpc_options.port is None

    with legacy_explore(
        foundry.kevm,
        kcfg_semantics=KEVMSemantics(),
        id=apr_proof.id,
        bug_report=bug_report,
        kore_rpc_command=rpc_options.kore_rpc_command,
        llvm_definition_dir=foundry.llvm_library if rpc_options.use_booster else None,
        smt_timeout=rpc_options.smt_timeout,
        smt_retry_limit=rpc_options.smt_retry_limit,
        smt_tactic=rpc_options.smt_tactic,
        trace_rewrites=rpc_options.trace_rewrites,
        start_server=start_server,
        port=rpc_options.port,
        maude_port=rpc_options.maude_port,
    ) as kcfg_explore:
        new_term, _ = kcfg_explore.cterm_simplify(cterm)
    if replace:
        apr_proof.kcfg.replace_node(node, new_term)
        apr_proof.write_proof_data()
    res_term = minimize_term(new_term.kast) if minimize else new_term.kast
    return foundry.kevm.pretty_print(res_term, unalias=False, sort_collections=sort_collections)


def foundry_merge_nodes(
    foundry: Foundry,
    test: str,
    node_ids: Iterable[NodeIdLike],
    version: int | None = None,
    bug_report: BugReport | None = None,
    include_disjunct: bool = False,
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

    test_id = foundry.get_test_id(test, version)
    apr_proof = foundry.get_apr_proof(test_id)

    if len(list(node_ids)) < 2:
        raise ValueError(f'Must supply at least 2 nodes to merge, got: {node_ids}')

    nodes = [apr_proof.kcfg.node(int(node_id)) for node_id in node_ids]
    check_cells = ['K_CELL', 'PROGRAM_CELL', 'PC_CELL', 'CALLDEPTH_CELL']
    check_cells_ne = [check_cell for check_cell in check_cells if not check_cells_equal(check_cell, nodes)]
    if check_cells_ne:
        raise ValueError(f'Nodes {node_ids} cannot be merged because they differ in: {check_cells_ne}')

    anti_unification = nodes[0].cterm
    for node in nodes[1:]:
        anti_unification, _, _ = anti_unification.anti_unify(node.cterm, keep_values=True, kdef=foundry.kevm.definition)
    new_node = apr_proof.kcfg.create_node(anti_unification)
    for node in nodes:
        apr_proof.kcfg.create_cover(node.id, new_node.id)

    apr_proof.write_proof_data()

    print(f'Merged nodes {node_ids} into new node {new_node.id}.')
    print(foundry.kevm.pretty_print(new_node.cterm.kast))


def foundry_step_node(
    foundry: Foundry,
    test: str,
    node: NodeIdLike,
    rpc_options: RPCOptions,
    version: int | None = None,
    repeat: int = 1,
    depth: int = 1,
    bug_report: BugReport | None = None,
) -> None:
    if repeat < 1:
        raise ValueError(f'Expected positive value for --repeat, got: {repeat}')
    if depth < 1:
        raise ValueError(f'Expected positive value for --depth, got: {depth}')

    test_id = foundry.get_test_id(test, version)
    apr_proof = foundry.get_apr_proof(test_id)
    start_server = rpc_options.port is None

    with legacy_explore(
        foundry.kevm,
        kcfg_semantics=KEVMSemantics(),
        id=apr_proof.id,
        bug_report=bug_report,
        kore_rpc_command=rpc_options.kore_rpc_command,
        llvm_definition_dir=foundry.llvm_library if rpc_options.use_booster else None,
        smt_timeout=rpc_options.smt_timeout,
        smt_retry_limit=rpc_options.smt_retry_limit,
        smt_tactic=rpc_options.smt_tactic,
        trace_rewrites=rpc_options.trace_rewrites,
        start_server=start_server,
        port=rpc_options.port,
        maude_port=rpc_options.maude_port,
    ) as kcfg_explore:
        for _i in range(repeat):
            node = kcfg_explore.step(apr_proof.kcfg, node, apr_proof.logs, depth=depth)
            apr_proof.write_proof_data()


def foundry_summary(
    name: str,
    accesses_file: Path,
    contract_names: Path | None,
    output_dir_name: str | None,
    foundry: Foundry,
    condense_summary: bool = False,
) -> None:
    if not accesses_file.exists():
        raise FileNotFoundError('Given account accesses dictionary file not found.')
    accesses = json.loads(accesses_file.read_text())['accountAccesses']
    accounts = {}
    if contract_names is not None:
        if not contract_names.exists():
            raise FileNotFoundError('Given contract names dictionary file not found.')
        accounts = json.loads(contract_names.read_text())
    summary_contract = DeploymentSummary(name=name, accounts=accounts)
    for access in accesses:
        summary_contract.add_cheatcode(access)

    if output_dir_name is None:
        output_dir_name = foundry.profile.get('test', '')

    output_dir = foundry._root / output_dir_name
    ensure_dir_path(output_dir)

    main_file = output_dir / Path(name + '.sol')

    if condense_summary:
        main_file.write_text('\n'.join(summary_contract.generate_condensed_file()))
    else:
        code_file = output_dir / Path(name + 'Code.sol')
        main_file.write_text('\n'.join(summary_contract.generate_main_contract_file()))
        code_file.write_text('\n'.join(summary_contract.generate_code_contract_file()))


def foundry_section_edge(
    foundry: Foundry,
    test: str,
    edge: tuple[str, str],
    rpc_options: RPCOptions,
    version: int | None = None,
    sections: int = 2,
    replace: bool = False,
    bug_report: BugReport | None = None,
) -> None:
    test_id = foundry.get_test_id(test, version)
    apr_proof = foundry.get_apr_proof(test_id)
    source_id, target_id = edge
    start_server = rpc_options.port is None

    with legacy_explore(
        foundry.kevm,
        kcfg_semantics=KEVMSemantics(),
        id=apr_proof.id,
        bug_report=bug_report,
        kore_rpc_command=rpc_options.kore_rpc_command,
        llvm_definition_dir=foundry.llvm_library if rpc_options.use_booster else None,
        smt_timeout=rpc_options.smt_timeout,
        smt_retry_limit=rpc_options.smt_retry_limit,
        smt_tactic=rpc_options.smt_tactic,
        trace_rewrites=rpc_options.trace_rewrites,
        start_server=start_server,
        port=rpc_options.port,
        maude_port=rpc_options.maude_port,
    ) as kcfg_explore:
        kcfg_explore.section_edge(
            apr_proof.kcfg, source_id=int(source_id), target_id=int(target_id), logs=apr_proof.logs, sections=sections
        )
    apr_proof.write_proof_data()


def foundry_get_model(
    foundry: Foundry,
    test: str,
    rpc_options: RPCOptions,
    version: int | None = None,
    nodes: Iterable[NodeIdLike] = (),
    pending: bool = False,
    failing: bool = False,
    bug_report: BugReport | None = None,
) -> str:
    test_id = foundry.get_test_id(test, version)
    proof = foundry.get_apr_proof(test_id)

    if not nodes:
        _LOGGER.warning('Node ID is not provided. Displaying models of failing and pending nodes:')
        failing = pending = True

    if pending:
        nodes = list(nodes) + [node.id for node in proof.pending]
    if failing:
        nodes = list(nodes) + [node.id for node in proof.failing]
    nodes = unique(nodes)

    res_lines = []

    start_server = rpc_options.port is None

    with legacy_explore(
        foundry.kevm,
        kcfg_semantics=KEVMSemantics(),
        id=proof.id,
        bug_report=bug_report,
        kore_rpc_command=rpc_options.kore_rpc_command,
        llvm_definition_dir=foundry.llvm_library if rpc_options.use_booster else None,
        smt_timeout=rpc_options.smt_timeout,
        smt_retry_limit=rpc_options.smt_retry_limit,
        smt_tactic=rpc_options.smt_tactic,
        trace_rewrites=rpc_options.trace_rewrites,
        start_server=start_server,
        port=rpc_options.port,
        maude_port=rpc_options.maude_port,
    ) as kcfg_explore:
        for node_id in nodes:
            res_lines.append('')
            res_lines.append(f'Node id: {node_id}')
            node = proof.kcfg.node(node_id)
            res_lines.extend(print_model(node, kcfg_explore))

    return '\n'.join(res_lines)


def _write_cfg(cfg: KCFG, path: Path) -> None:
    path.write_text(cfg.to_json())
    _LOGGER.info(f'Updated CFG file: {path}')


class FoundryNodePrinter(KEVMNodePrinter):
    foundry: Foundry
    contract_name: str

    def __init__(self, foundry: Foundry, contract_name: str):
        KEVMNodePrinter.__init__(self, foundry.kevm)
        self.foundry = foundry
        self.contract_name = contract_name

    def print_node(self, kcfg: KCFG, node: KCFG.Node) -> list[str]:
        ret_strs = super().print_node(kcfg, node)
        _pc = node.cterm.try_cell('PC_CELL')
        if type(_pc) is KToken and _pc.sort == INT:
            srcmap_data = self.foundry.srcmap_data(self.contract_name, int(_pc.token))
            if srcmap_data is not None:
                path, start, end = srcmap_data
                ret_strs.append(f'src: {str(path)}:{start}:{end}')
        return ret_strs


class FoundryAPRNodePrinter(FoundryNodePrinter, APRProofNodePrinter):
    def __init__(self, foundry: Foundry, contract_name: str, proof: APRProof):
        FoundryNodePrinter.__init__(self, foundry, contract_name)
        APRProofNodePrinter.__init__(self, proof, foundry.kevm)


class FoundryAPRBMCNodePrinter(FoundryNodePrinter, APRBMCProofNodePrinter):
    def __init__(self, foundry: Foundry, contract_name: str, proof: APRBMCProof):
        FoundryNodePrinter.__init__(self, foundry, contract_name)
        APRBMCProofNodePrinter.__init__(self, proof, foundry.kevm)


def foundry_node_printer(foundry: Foundry, contract_name: str, proof: APRProof) -> NodePrinter:
    if type(proof) is APRBMCProof:
        return FoundryAPRBMCNodePrinter(foundry, contract_name, proof)
    if type(proof) is APRProof:
        return FoundryAPRNodePrinter(foundry, contract_name, proof)
    raise ValueError(f'Cannot build NodePrinter for proof type: {type(proof)}')
