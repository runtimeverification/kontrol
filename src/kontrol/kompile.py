from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk.kevm import KEVM
from kevm_pyk.kompile import kevm_kompile
from pyk.kast.outer import KDefinition, KFlatModule, KImport, KRequire
from pyk.kdist import kdist
from pyk.utils import ensure_dir_path, hash_str

from . import VERSION
from .kdist.utils import KSRC_DIR
from .solc_to_k import Contract, contract_to_main_module, contract_to_verification_module
from .utils import _read_digest_file, _rv_blue, console, kontrol_up_to_date

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
    kompiled_timestamp = foundry.kompiled / 'timestamp'
    main_module = 'KONTROL-BASE'
    if options.keccak_lemmas and not options.auxiliary_lemmas:
        main_module = 'KONTROL-KECCAK'
    elif not options.keccak_lemmas and options.auxiliary_lemmas:
        main_module = 'KONTROL-AUX'
    else:
        main_module = 'KONTROL-FULL'
    includes = [Path(include) for include in options.includes if Path(include).exists()] + [KSRC_DIR]

    if options.forge_build:
        foundry.build(options.metadata)

    if options.silence_warnings:
        options.ignore_warnings = _silenced_warnings()

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

    def kompilation_digest() -> str:
        k_files = [foundry.contracts_file, foundry.main_file]
        return hash_str(''.join([hash_str(Path(k_file).read_text()) for k_file in k_files]))

    def kompilation_up_to_date() -> bool:
        if not foundry.digest_file.exists():
            return False
        digest_dict = _read_digest_file(foundry.digest_file)
        return digest_dict.get('kompilation', '') == kompilation_digest()

    def update_kompilation_digest() -> None:
        digest_dict = _read_digest_file(foundry.digest_file)
        digest_dict['kompilation'] = kompilation_digest()
        digest_dict['kontrol'] = VERSION
        digest_dict['build-options'] = str(options)
        foundry.digest_file.write_text(json.dumps(digest_dict, indent=4))

        _LOGGER.info('Updated Kompilation digest')

    def should_rekompile() -> bool:
        if options.rekompile or not kompiled_timestamp.exists():
            return True

        return not (kompilation_up_to_date() and foundry.up_to_date() and kontrol_up_to_date(foundry.digest_file))

    if should_rekompile():
        output_dir = foundry.kompiled

        optimization = 0
        if options.o1:
            optimization = 1
        if options.o2:
            optimization = 2
        if options.o3:
            optimization = 3

        kevm_kompile(
            target=options.target,
            output_dir=output_dir,
            main_file=foundry.main_file,
            main_module=main_module,
            syntax_module=options.syntax_module,
            includes=includes,
            emit_json=True,
            ccopts=options.ccopts,
            debug=options.debug,
            verbose=options.verbose,
            ignore_warnings=options.ignore_warnings,
            optimization=optimization,
        )

    update_kompilation_digest()
    foundry.update_digest()


def _foundry_to_contract_def(
    contracts: Iterable[Contract],
    requires: Iterable[str],
    enums: dict[str, int],
) -> KDefinition:
    modules = [contract_to_main_module(contract, imports=['KONTROL-BASE'], enums=enums) for contract in contracts]
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
