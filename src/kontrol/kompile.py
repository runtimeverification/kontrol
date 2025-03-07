from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk.kevm import KEVM
from pyk.kast.outer import KDefinition, KFlatModule, KImport, KRequire
from pyk.kdist import kdist
from pyk.utils import ensure_dir_path

from .kdist.utils import KSRC_DIR
from .solc_to_k import Contract, contract_to_main_module, contract_to_verification_module
from .utils import _rv_blue, console

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Final

    from .foundry import Foundry
    from .options import BuildOptions

_LOGGER: Final = logging.getLogger(__name__)


def foundry_kompile(
    options: BuildOptions,
    foundry: Foundry,
) -> None:
    foundry_requires_dir = foundry.kompiled / 'requires'
    foundry.kompiled / 'timestamp'
    main_module = 'KONTROL-BASE'
    if options.keccak_lemmas and not options.auxiliary_lemmas:
        main_module = 'KONTROL-KECCAK'
    elif not options.keccak_lemmas and options.auxiliary_lemmas:
        main_module = 'KONTROL-AUX'
    else:
        main_module = 'KONTROL-FULL'
    [Path(include) for include in options.includes if Path(include).exists()] + [KSRC_DIR]

    if options.forge_build:
        foundry.build(options.metadata)

    ensure_dir_path(foundry.kompiled)
    ensure_dir_path(foundry_requires_dir)

    regen = options.regen
    foundry_up_to_date = True

    if not foundry.up_to_date():
        _LOGGER.info('Detected updates to contracts, regenerating K definition.')
        regen = True
        foundry_up_to_date = False

    if regen or not foundry.contracts_file.exists() or not foundry.main_file.exists():
        if regen and foundry_up_to_date:
            console.print(
                f'[{_rv_blue()}][bold]--regen[/bold] option provided. Rebuilding Kontrol Project.[/{_rv_blue()}]'
            )

        bin_runtime_definition = _foundry_to_contract_def(
            contracts=foundry.contracts.values(),
            requires=['kontrol.md'],
            enums=foundry.enums,
        )

        contract_main_definition = _foundry_to_main_def(
            main_module=main_module,
            contracts=foundry.contracts.values(),
            requires=['contracts.k'],
            keccak_lemmas=options.keccak_lemmas,
            auxiliary_lemmas=options.auxiliary_lemmas,
        )

        kevm = KEVM(
            kdist.get('kontrol.base'),
            extra_unparsing_modules=(bin_runtime_definition.all_modules + contract_main_definition.all_modules),
        )

        foundry.contracts_file.write_text(kevm.pretty_print(bin_runtime_definition, unalias=False) + '\n')
        _LOGGER.info(f'Wrote file: {foundry.contracts_file}')
        foundry.main_file.write_text(kevm.pretty_print(contract_main_definition) + '\n')
        _LOGGER.info(f'Wrote file: {foundry.main_file}')

        foundry.contracts_file_json.write_text(json.dumps(bin_runtime_definition.to_json()))
        _LOGGER.info(f'Wrote file: {foundry.contracts_file_json}')
        foundry.main_file_json.write_text(json.dumps(contract_main_definition.to_json()))
        _LOGGER.info(f'Wrote file: {foundry.main_file_json}')

    foundry.update_digest()


def _foundry_to_contract_def(
    contracts: Iterable[Contract],
    requires: Iterable[str],
    enums: dict[str, int],
) -> KDefinition:
    modules = [contract_to_main_module(contract, imports=['KONTROL-BASE']) for contract in contracts]
    # First module is chosen as main module arbitrarily, since the contract definition is just a set of
    # contract modules.
    main_module = Contract.contract_to_module_name(list(contracts)[0].name_with_path)

    return KDefinition(
        main_module,
        modules,
        requires=(KRequire(req) for req in list(requires)),
    )


def _foundry_to_main_def(
    main_module: str,
    contracts: Iterable[Contract],
    requires: Iterable[str],
    keccak_lemmas: bool,
    auxiliary_lemmas: bool,
) -> KDefinition:
    modules = [contract_to_verification_module(contract) for contract in contracts]
    _main_module = KFlatModule(
        main_module,
        imports=tuple(
            [KImport(mname) for mname in (_m.name for _m in modules)]
            + ([KImport('KECCAK-LEMMAS')] if keccak_lemmas else [])
            + ([KImport('KONTROL-AUX-LEMMAS')] if auxiliary_lemmas else [])
        ),
    )

    return KDefinition(
        main_module,
        [_main_module] + modules,
        requires=(KRequire(req) for req in list(requires)),
    )


def _silenced_warnings() -> list[str]:
    return ['non-exhaustive-match', 'missing-syntax-module']
