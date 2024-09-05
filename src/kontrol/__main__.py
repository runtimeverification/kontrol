from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterable
from typing import TYPE_CHECKING

from pyk.cli.pyk import parse_toml_args
from pyk.cterm.symbolic import CTermSMTError
from pyk.proof.reachability import APRFailureInfo, APRProof
from pyk.proof.tui import APRProofViewer
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler

from . import VERSION
from .cli import _create_argument_parser, generate_options, get_argument_type_setter, get_option_string_destination
from .foundry import (
    Foundry,
    foundry_clean,
    foundry_get_model,
    foundry_list,
    foundry_merge_nodes,
    foundry_minimize_proof,
    foundry_node_printer,
    foundry_refute_node,
    foundry_remove_node,
    foundry_section_edge,
    foundry_show,
    foundry_simplify_node,
    foundry_split_node,
    foundry_state_load,
    foundry_step_node,
    foundry_to_dot,
    foundry_unrefute_node,
    init_project,
    read_recorded_state_diff,
    read_recorded_state_dump,
)
from .hevm import Hevm
from .kompile import foundry_kompile
from .prove import foundry_prove
from .solc import CompilationUnit
from .solc_to_k import solc_compile, solc_to_k
from .utils import _LOG_FORMAT, _rv_blue, _rv_yellow, check_k_version, config_file_path, console, loglevel

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final, TypeVar

    from pyk.cterm import CTerm
    from pyk.kcfg.tui import KCFGElem
    from pyk.utils import BugReport

    from .options import (
        BuildOptions,
        CleanOptions,
        CompileOptions,
        GetModelOptions,
        InitOptions,
        ListOptions,
        LoadStateOptions,
        MergeNodesOptions,
        MinimizeProofOptions,
        ProveOptions,
        RefuteNodeOptions,
        RemoveNodeOptions,
        SectionEdgeOptions,
        ShowOptions,
        SimplifyNodeOptions,
        SolcToKOptions,
        SplitNodeOptions,
        StepNodeOptions,
        ToDotOptions,
        UnrefuteNodeOptions,
        VersionOptions,
        ViewKcfgOptions,
    )

    T = TypeVar('T')

_LOGGER: Final = logging.getLogger(__name__)


def _load_foundry(
    foundry_root: Path,
    bug_report: BugReport | None = None,
    use_hex_encoding: bool = False,
    add_enum_constraints: bool = False,
    expand_config: bool = False,
) -> Foundry:
    try:
        foundry = Foundry(
            foundry_root=foundry_root,
            bug_report=bug_report,
            use_hex_encoding=use_hex_encoding,
            add_enum_constraints=add_enum_constraints,
            expand_config=expand_config,
        )
    except FileNotFoundError:
        print(
            f'File foundry.toml not found in: {str(foundry_root)!r}. Are you running kontrol in a Foundry project?',
            file=sys.stderr,
        )
        sys.exit(127)
    return foundry


def main() -> None:
    sys.setrecursionlimit(15000000)
    parser = _create_argument_parser()
    args = parser.parse_args()
    args.config_file = config_file_path(args)
    toml_args = parse_toml_args(args, get_option_string_destination, get_argument_type_setter)
    logging.basicConfig(
        level=loglevel(args, toml_args),
        format=_LOG_FORMAT,
        handlers=[
            RichHandler(
                level=loglevel(args, toml_args),
                show_level=False,
                show_time=False,
                show_path=False,
                highlighter=NullHighlighter(),
            ),
        ],
    )

    check_k_version()

    stripped_args = toml_args | {
        key: val for (key, val) in vars(args).items() if val is not None and not (isinstance(val, Iterable) and not val)
    }
    options = generate_options(stripped_args)

    executor_name = 'exec_' + args.command.lower().replace('-', '_')
    if executor_name not in globals():
        raise AssertionError(f'Unimplemented command: {args.command}')

    execute = globals()[executor_name]
    execute(options)


# Command implementation


def exec_load_state(options: LoadStateOptions) -> None:
    foundry_state_load(
        options=options,
        foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
    )


def exec_version(options: VersionOptions) -> None:
    print(f'Kontrol version: {VERSION}')


def exec_compile(options: CompileOptions) -> None:
    res = solc_compile(options.contract_file)
    print(json.dumps(res))


def exec_solc_to_k(options: SolcToKOptions) -> None:
    k_text = solc_to_k(options)
    print(k_text)


def exec_build(options: BuildOptions) -> None:
    _LOGGER.debug(options)

    if options.verbose or options.debug:
        building_message = f'[{_rv_blue()}]:hammer: [bold]Building [{_rv_yellow()}]Kontrol[/{_rv_yellow()}] project[/bold] :hammer:[/{_rv_blue()}]'
    else:
        building_message = f'[{_rv_blue()}]:hammer: [bold]Building [{_rv_yellow()}]Kontrol[/{_rv_yellow()}] project[/bold] :hammer: \n Add `--verbose` to `kontrol build` for more details![/{_rv_blue()}]'
    try:
        console.print(building_message)
        foundry_kompile(
            options=options,
            foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
        )
        console.print(
            ':white_heavy_check_mark: [bold green]Success![/bold green] [bold]Kontrol project built[/bold] :muscle:'
        )
    except Exception as e:
        console.print(f'[bold red]An error occurred while building your Kontrol project:[/bold red] [black]{e}[/black]')


def exec_prove(options: ProveOptions) -> None:
    _LOGGER.debug(options)

    if options.recorded_diff_state_path and options.recorded_dump_state_path:
        raise AssertionError('Provide only one file for recorded state updates')

    recorded_diff_entries = (
        read_recorded_state_diff(options.recorded_diff_state_path) if options.recorded_diff_state_path else None
    )
    recorded_dump_entries = (
        read_recorded_state_dump(options.recorded_dump_state_path) if options.recorded_dump_state_path else None
    )

    if options.verbose or options.debug:
        proving_message = f'[{_rv_blue()}]:person_running: [bold]Running [{_rv_yellow()}]Kontrol[/{_rv_yellow()}] proofs[/bold] :person_running:[/{_rv_blue()}]'
    else:
        proving_message = f'[{_rv_blue()}]:person_running: [bold]Running [{_rv_yellow()}]Kontrol[/{_rv_yellow()}] proofs[/bold] :person_running: \n Add `--verbose` to `kontrol prove` for more details![/{_rv_blue()}]'
    try:
        console.print(proving_message)
        results = foundry_prove(
            foundry=_load_foundry(
                options.foundry_root, options.bug_report, add_enum_constraints=options.enum_constraints
            ),
            options=options,
            recorded_state_entries=recorded_dump_entries if recorded_dump_entries else recorded_diff_entries,
        )
    except CTermSMTError as err:
        raise RuntimeError(
            f'SMT solver error; SMT timeout occured. SMT timeout parameter is currently set to {options.smt_timeout}ms, you may increase it using "--smt-timeout" command line argument. Related KAST pattern provided below:\n{err.message}'
        ) from err

    failed = 0
    for proof in results:
        _, test = proof.id.split('.')
        if not any(test.startswith(prefix) for prefix in ['test', 'check', 'prove']):
            signature, _ = test.split(':')
            _LOGGER.warning(
                f"{signature} is not prefixed with 'test', 'prove', or 'check', therefore, it is not reported as failing in the presence of reverts or assertion violations."
            )
        if proof.passed:
            console.print(f':sparkles: [bold green]PROOF PASSED[/bold green] :sparkles: {proof.id}')
            console.print(
                f':hourglass_not_done: [bold blue]Time: {proof.formatted_exec_time()}[/bold blue] :hourglass_not_done:'
            )
        else:
            failed += 1
            console.print(f':cross_mark: [bold red]PROOF FAILED[/bold red] :cross_mark: {proof.id}')
            console.print(
                f':hourglass_not_done: [bold blue]Time: {proof.formatted_exec_time()}[/bold blue] :hourglass_not_done:'
            )
            failure_log = None
            if isinstance(proof, APRProof) and isinstance(proof.failure_info, APRFailureInfo):
                failure_log = proof.failure_info
            if options.failure_info and failure_log is not None:
                log = failure_log.print() + (Foundry.help_info() if not options.hevm else Hevm.help_info(proof.id))
                for line in log:
                    print(line)
            refuted_nodes = list(proof.node_refutations.keys())
            if len(refuted_nodes) > 0:
                print(f'The proof cannot be completed while there are refuted nodes: {refuted_nodes}.')
                print('Either unrefute the nodes or discharge the corresponding refutation subproofs.')

    sys.exit(1 if failed else 0)


def exec_show(options: ShowOptions) -> None:
    output = foundry_show(
        foundry=_load_foundry(
            options.foundry_root,
            use_hex_encoding=options.use_hex_encoding,
            add_enum_constraints=options.enum_constraints,
            expand_config=options.expand_config,
        ),
        options=options,
    )
    print(output)


def exec_refute_node(options: RefuteNodeOptions) -> None:
    foundry = _load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints)
    refutation = foundry_refute_node(foundry=foundry, options=options)

    if refutation:
        claim, _ = refutation.to_claim('refuted-' + str(options.node))
        print('\nClaim for the refutation:\n')
        print(foundry.kevm.pretty_print(claim))
        print('\n')
    else:
        raise ValueError(f'Unable to refute node for test {options.test}: {options.node}')


def exec_unrefute_node(options: UnrefuteNodeOptions) -> None:
    foundry_unrefute_node(
        foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
        options=options,
    )


def exec_split_node(options: SplitNodeOptions) -> None:
    node_ids = foundry_split_node(
        foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
        options=options,
    )

    print(f'Node {options.node} has been split into {node_ids} on condition {options.branch_condition}.')


def exec_to_dot(options: ToDotOptions) -> None:
    foundry_to_dot(
        foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
        options=options,
    )


def exec_list(options: ListOptions) -> None:
    stats = foundry_list(foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints))
    print('\n'.join(stats))


def exec_view_kcfg(options: ViewKcfgOptions) -> None:
    foundry = _load_foundry(
        options.foundry_root, use_hex_encoding=options.use_hex_encoding, add_enum_constraints=options.enum_constraints
    )
    test_id = foundry.get_test_id(options.test, options.version)
    contract_name, _ = test_id.split('.')
    proof = foundry.get_apr_proof(test_id)

    compilation_unit = CompilationUnit.load_build_info(options.foundry_root)

    def _short_info(cterm: CTerm) -> Iterable[str]:
        return foundry.short_info_for_contract(contract_name, cterm)

    def _custom_view(elem: KCFGElem) -> Iterable[str]:
        return foundry.custom_view(contract_name, elem, compilation_unit)

    node_printer = foundry_node_printer(foundry, contract_name, proof)
    viewer = APRProofViewer(proof, foundry.kevm, node_printer=node_printer, custom_view=_custom_view)
    viewer.run()


def exec_minimize_proof(options: MinimizeProofOptions) -> None:
    foundry_minimize_proof(
        foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
        options=options,
    )


def exec_remove_node(options: RemoveNodeOptions) -> None:
    foundry_remove_node(
        foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
        options=options,
    )


def exec_simplify_node(options: SimplifyNodeOptions) -> None:

    pretty_term = foundry_simplify_node(
        foundry=_load_foundry(options.foundry_root, options.bug_report, add_enum_constraints=options.enum_constraints),
        options=options,
    )
    print(f'Simplified:\n{pretty_term}')


def exec_step_node(options: StepNodeOptions) -> None:
    foundry_step_node(
        foundry=_load_foundry(options.foundry_root, options.bug_report, add_enum_constraints=options.enum_constraints),
        options=options,
    )


def exec_merge_nodes(options: MergeNodesOptions) -> None:
    foundry_merge_nodes(
        foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
        options=options,
    )


def exec_section_edge(options: SectionEdgeOptions) -> None:

    foundry_section_edge(
        foundry=_load_foundry(options.foundry_root, options.bug_report, add_enum_constraints=options.enum_constraints),
        options=options,
    )


def exec_get_model(options: GetModelOptions) -> None:

    output = foundry_get_model(
        foundry=_load_foundry(options.foundry_root, add_enum_constraints=options.enum_constraints),
        options=options,
    )
    print(output)


def exec_clean(options: CleanOptions) -> None:
    foundry_clean(foundry=_load_foundry(options.foundry_root), options=options)


def exec_init(options: InitOptions) -> None:
    init_project(project_root=options.project_root, skip_forge=options.skip_forge)


if __name__ == '__main__':
    main()
