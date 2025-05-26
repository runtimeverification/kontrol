from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk.kevm import KEVM, KEVMNodePrinter
from kevm_pyk.utils import legacy_explore, print_failure_info
from pyk.cterm import CTerm
from pyk.cterm.show import CTermShow
from pyk.kast.inner import KApply, KToken, KVariable
from pyk.kast.manip import collect, extract_lhs, flatten_label
from pyk.kast.outer import KDefinition, KFlatModule, KImport, KRequire
from pyk.kast.prelude.kint import INT
from pyk.kast.pretty import PrettyPrinter
from pyk.kcfg import KCFG
from pyk.kcfg.minimize import KCFGMinimizer
from pyk.proof.reachability import APRProof
from pyk.proof.show import APRProofNodePrinter, APRProofShow
from pyk.proof.tui import APRProofViewer
from pyk.utils import single, unique

from .foundry import Foundry, KontrolSemantics
from .solc import CompilationUnit
from .solc_to_k import Contract

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Final

    from pyk.kast.inner import KInner
    from pyk.kcfg.show import NodePrinter
    from pyk.kcfg.tui import KCFGElem

    from .options import ShowOptions, ViewKcfgOptions

_LOGGER: Final = logging.getLogger(__name__)


class FoundryNodePrinter(KEVMNodePrinter):
    foundry: Foundry
    contract_name: str
    compilation_unit: CompilationUnit

    def __init__(self, foundry: Foundry, cterm_show: CTermShow, contract_name: str):
        KEVMNodePrinter.__init__(self, foundry.kevm, cterm_show)
        self.foundry = foundry
        self.contract_name = contract_name
        self.compilation_unit = CompilationUnit.load_build_info(foundry.build_info)

    def print_node(self, kcfg: KCFG, node: KCFG.Node) -> list[str]:
        ret_strs = super().print_node(kcfg, node)
        _pc = node.cterm.try_cell('PC_CELL')
        program_cell = node.cterm.try_cell('PROGRAM_CELL')

        if type(_pc) is KToken and _pc.sort == INT:
            if type(program_cell) is KToken:
                try:
                    bytecode = ast.literal_eval(program_cell.token)
                    instruction = self.compilation_unit.get_instruction(bytecode, int(_pc.token))
                    ast_node = instruction.node()
                    start_line, _, end_line, _ = ast_node.source_range()
                    ret_strs.append(f'src: {str(Path(ast_node.source.name))}:{start_line}:{end_line}')
                except Exception:
                    pass

        calldata_cell = node.cterm.try_cell('CALLDATA_CELL')

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
    def __init__(self, foundry: Foundry, cterm_show: CTermShow, contract_name: str, proof: APRProof):
        FoundryNodePrinter.__init__(self, foundry, cterm_show, contract_name)
        APRProofNodePrinter.__init__(self, proof, cterm_show)


def foundry_node_printer(foundry: Foundry, cterm_show: CTermShow, contract_name: str, proof: APRProof) -> NodePrinter:
    if type(proof) is APRProof:
        return FoundryAPRNodePrinter(foundry, cterm_show, contract_name, proof)
    raise ValueError(f'Cannot build NodePrinter for proof type: {type(proof)}')


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
    omit_cells = unstable_cells if options.omit_unstable_output else []

    printer = PrettyPrinter(
        foundry.kevm.definition,
        sort_collections=options.sort_collections,
        patch_symbol_table=KEVM._kevm_patch_symbol_table,
    )
    cterm_show = CTermShow(printer.print, minimize=True, omit_labels=omit_cells)
    node_printer = foundry_node_printer(foundry, cterm_show, contract_name, proof)
    proof_show = APRProofShow(foundry.kevm.definition, node_printer=node_printer)

    if options.minimize_kcfg:
        KCFGMinimizer(proof.kcfg).minimize()

    res_lines = proof_show.show(
        proof,
        nodes=nodes,
        node_deltas=options.node_deltas,
        to_module=options.to_module,
        omit_cells=omit_cells,
        minimize=options.minimize,
    )

    start_server = options.port is None

    if options.failure_info:
        with legacy_explore(
            foundry.kevm,
            kcfg_semantics=KontrolSemantics(),
            id=test_id,
            smt_timeout=options.smt_timeout,
            smt_retry_limit=options.smt_retry_limit,
            start_server=start_server,
            port=options.port,
            extra_module=foundry.load_lemmas(options.lemmas),
        ) as kcfg_explore:
            res_lines += print_failure_info(proof, kcfg_explore, options.counterexample_info)
            res_lines += Foundry.help_info(proof.id, False)

    if options.to_kevm_claims or options.to_kevm_rules:
        _foundry_labels = [
            prod.klabel
            for prod in foundry.kevm.definition.all_modules_dict['FOUNDRY-CHEAT-CODES'].productions
            if prod.klabel is not None
        ]

        def _remove_foundry_config(_cterm: CTerm) -> CTerm:
            kevm_config_pattern = KApply(
                '<generatedTop>',
                [
                    KApply(
                        '<foundry>',
                        [
                            KVariable('KEVM_CELL'),
                            KVariable('STACKCHECKS_CELL'),
                            KVariable('CHEATCODES_CELL'),
                            KVariable('KEVMTRACING_CELL'),
                        ],
                    ),
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

        sentences = [
            edge.to_rule(
                'BASIC-BLOCK',
                claim=(not options.to_kevm_rules),
                defunc_with=foundry.kevm.definition,
                minimize=options.minimize,
            )
            for edge in proof.kcfg.edges()
        ]
        sentences = [sent for sent in sentences if not _contains_foundry_klabel(sent.body)]
        sentences = [
            sent for sent in sentences if not KontrolSemantics().is_terminal(CTerm.from_kast(extract_lhs(sent.body)))
        ]
        if len(sentences) == 0:
            _LOGGER.warning(f'No claims or rules retained for proof {proof.id}')

        else:
            module_name = Contract.escaped(proof.id.upper() + '-SPEC', '')
            module = KFlatModule(module_name, sentences=sentences, imports=[KImport('VERIFICATION')])
            defn = KDefinition(module_name, [module], requires=[KRequire('verification.k')])

            defn_lines = foundry.kevm.pretty_print(defn, in_module='EVM').split('\n')

            res_lines += defn_lines

            if options.kevm_claim_dir is not None:
                kevm_sentences_file = options.kevm_claim_dir / (module_name.lower() + '.k')
                kevm_sentences_file.write_text('\n'.join(line.rstrip() for line in defn_lines))

    return '\n'.join([line.rstrip() for line in res_lines])


def solidity_src_print(path: Path, start: int, end: int) -> Iterable[str]:
    lines = path.read_text().split('\n')
    prefix_lines = [f'   {l}' for l in lines[:start]]
    actual_lines = [f' | {l}' for l in lines[start:end]]
    suffix_lines = [f'   {l}' for l in lines[end:]]
    return prefix_lines + actual_lines + suffix_lines


def custom_view(contract_name: str, element: KCFGElem, compilation_unit: CompilationUnit) -> Iterable[str]:
    if type(element) is KCFG.Node:
        pc_cell = element.cterm.try_cell('PC_CELL')
        program_cell = element.cterm.try_cell('PROGRAM_CELL')
        if type(pc_cell) is KToken and pc_cell.sort == INT:
            if type(program_cell) is KToken:
                try:
                    bytecode = ast.literal_eval(program_cell.token)
                    instruction = compilation_unit.get_instruction(bytecode, int(pc_cell.token))
                    node = instruction.node()
                    start_line, _, end_line, _ = node.source_range()
                    return solidity_src_print(Path(node.source.name), start_line - 1, end_line)
                except Exception:
                    return [f'No sourcemap data for contract at pc {contract_name}: {int(pc_cell.token)}']
            return ['NO DATA']
    elif type(element) is KCFG.Edge:
        return list(element.rules)
    elif type(element) is KCFG.NDBranch:
        return list(element.rules)
    return ['NO DATA']


def foundry_view(foundry: Foundry, options: ViewKcfgOptions) -> None:
    test_id = foundry.get_test_id(options.test, options.version)
    contract_name, _ = test_id.split('.')
    proof = foundry.get_apr_proof(test_id)

    compilation_unit = CompilationUnit.load_build_info(foundry.build_info)

    def _custom_view(elem: KCFGElem) -> Iterable[str]:
        return custom_view(contract_name, elem, compilation_unit)

    printer = PrettyPrinter(foundry.kevm.definition, patch_symbol_table=KEVM._kevm_patch_symbol_table)
    cterm_show = CTermShow(printer.print)
    node_printer = foundry_node_printer(foundry, cterm_show, contract_name, proof)

    viewer = APRProofViewer(proof, foundry.kevm, node_printer=node_printer, custom_view=_custom_view)
    viewer.run()
