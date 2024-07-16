from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .foundry import foundry_to_xml
from .prove import _run_cfg_group, collect_setup_methods, collect_tests
from .utils import console

if TYPE_CHECKING:
    from typing import Final

    from pyk.proof.reachability import APRProof

    from .foundry import Foundry
    from .options import FuzzOptions
    from .prove import FoundryTest

_LOGGER: Final = logging.getLogger(__name__)


def kontrol_fuzz(
    options: FuzzOptions,
    foundry: Foundry,
) -> list[APRProof]:
    foundry.mk_fuzz_dir()
    test_suite = collect_tests(foundry, options.tests, reinit=options.reinit, fuzzing=True)
    test_names = [test.name for test in test_suite]
    separator = '\n\t\t    '  # ad-hoc separator for the string "Selected functions: " below
    console.print(f'[bold]Selected functions:[/bold] {separator.join(test_names)}')

    contracts = [(test.contract, test.version) for test in test_suite]
    setup_method_tests = collect_setup_methods(
        foundry,
        contracts,
        reinit=options.reinit,
        setup_version=options.setup_version,
        fuzzing=True,
    )
    setup_method_names = [test.name for test in setup_method_tests]

    _LOGGER.info(f'Running tests: {test_names}')

    _LOGGER.info(f'Updating digests: {test_names}')
    for test in test_suite:
        test.method.update_digest(foundry.digest_file)

    _LOGGER.info(f'Updating digests: {setup_method_names}')
    for test in setup_method_tests:
        test.method.update_digest(foundry.digest_file)

    def _run_prover(_test_suite: list[FoundryTest], include_summaries: bool = False) -> list[APRProof]:
        return _run_cfg_group(
            tests=_test_suite,
            foundry=foundry,
            options=options,
            summary_ids=([]),
            recorded_state_entries=None,
            fuzzing=True,
        )

    # if options.run_constructor:
    #     constructor_tests = collect_constructors(foundry, contracts, reinit=options.reinit)
    #     constructor_names = [test.name for test in constructor_tests]

    #     _LOGGER.info(f'Updating digests: {constructor_names}')
    #     for test in constructor_tests:
    #         test.method.update_digest(foundry.digest_file)

    #     if options.verbose:
    #         _LOGGER.info(f'Running initialization code for contracts in parallel: {constructor_names}')
    #     else:
    #         console.print(f'[bold]Running initialization code for contracts in parallel:[/bold] {constructor_names}')

    #     results = _run_prover(constructor_tests, include_summaries=False)
    #     failed = [proof for proof in results if not proof.passed]
    #     if failed:
    #         raise ValueError(f'Running initialization code failed for {len(failed)} contracts: {failed}')

    if options.verbose:
        _LOGGER.info(f'Running setup functions in parallel: {setup_method_names}')
    else:
        separator = '\n\t\t\t\t     '  # ad-hoc separator for the string "Running setup functions in parallel: " below
        console.print(f'[bold]Running setup functions in parallel:[/bold] {separator.join(setup_method_names)}')
    results = _run_prover(setup_method_tests, include_summaries=False)

    failed = [proof for proof in results if not proof.passed]
    if failed:
        raise ValueError(f'Running setUp method failed for {len(failed)} contracts: {failed}')

    if options.verbose:
        _LOGGER.info(f'Running test functions in parallel: {test_names}')
    else:
        separator = '\n\t\t\t\t    '  # ad-hoc separator for the string "Running test functions in parallel: " below
        console.print(f'[bold]Running test functions in parallel:[/bold] {separator.join(test_names)}')
    results = _run_prover(test_suite, include_summaries=True)

    if options.xml_test_report:
        foundry_to_xml(foundry, results)

    return results
