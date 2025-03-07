from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyk.kast.outer import KDefinition, KFlatModule, KImport, KRequire
from pyk.utils import ensure_dir_path

from .solc_to_k import Contract, contract_to_main_module, contract_to_verification_module

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
    if options.forge_build:
        foundry.build(options.metadata)
    ensure_dir_path(foundry.kompiled)
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
