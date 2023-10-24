from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk import kdist
from kevm_pyk.kevm import KEVM
from kevm_pyk.kompile import KompileTarget, kevm_kompile
from pyk.kast.outer import KDefinition, KFlatModule, KImport, KRequire
from pyk.utils import ensure_dir_path, hash_str

from .foundry import Foundry
from .kdist.utils import KSRC_DIR
from .solc_to_k import Contract, contract_to_main_module, contract_to_verification_module

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Final

    from pyk.kast.inner import KInner

_LOGGER: Final = logging.getLogger(__name__)


def foundry_kompile(
    foundry_root: Path,
    includes: Iterable[str],
    regen: bool = False,
    rekompile: bool = False,
    requires: Iterable[str] = (),
    imports: Iterable[str] = (),
    ccopts: Iterable[str] = (),
    llvm_kompile: bool = True,
    debug: bool = False,
    verbose: bool = False,
    target: KompileTarget = KompileTarget.HASKELL_BOOSTER,
) -> None:
    syntax_module = 'FOUNDRY-CONTRACTS'
    foundry = Foundry(foundry_root)
    foundry_requires_dir = foundry.kompiled / 'requires'
    foundry_contracts_file = foundry.kompiled / 'contracts.k'
    kompiled_timestamp = foundry.kompiled / 'timestamp'
    main_module = 'FOUNDRY-MAIN'
    includes = [include for include in includes if Path(include).exists()] + [str(KSRC_DIR)]
    ensure_dir_path(foundry.kompiled)
    ensure_dir_path(foundry_requires_dir)

    requires_paths: dict[str, str] = {}

    foundry.build()

    if not foundry.up_to_date():
        _LOGGER.info('Detected updates to contracts, regenerating K definition.')
        regen = True

    for r in requires:
        req = Path(r)
        if not req.exists():
            raise ValueError(f'No such file: {req}')
        if req.name in requires_paths.keys():
            raise ValueError(
                f'Required K files have conflicting names: {r} and {requires_paths[req.name]}. Consider changing the name of one of these files.'
            )
        requires_paths[req.name] = r
        req_path = foundry_requires_dir / req.name
        if regen or not req_path.exists():
            _LOGGER.info(f'Copying requires path: {req} -> {req_path}')
            shutil.copy(req, req_path)
            regen = True

    _imports: dict[str, list[str]] = {contract.name: [] for contract in foundry.contracts.values()}
    for i in imports:
        imp = i.split(':')
        if not len(imp) == 2:
            raise ValueError(f'module imports must be of the form "[ContractName]:[MODULE-NAME]". Got: {i}')
        if imp[0] in _imports:
            _imports[imp[0]].append(imp[1])
        else:
            raise ValueError(f'Could not find contract: {imp[0]}')

    if regen or not foundry_contracts_file.exists() or not foundry.main_file.exists():
        copied_requires = []
        copied_requires += [f'requires/{name}' for name in list(requires_paths.keys())]
        imports = ['FOUNDRY']
        kevm = KEVM(kdist.get('foundry'))
        empty_config = kevm.definition.empty_config(Foundry.Sorts.FOUNDRY_CELL)
        bin_runtime_definition = _foundry_to_contract_def(
            empty_config=empty_config,
            contracts=foundry.contracts.values(),
            requires=['foundry.md'],
        )

        contract_main_definition = _foundry_to_main_def(
            main_module=main_module,
            empty_config=empty_config,
            contracts=foundry.contracts.values(),
            requires=(['contracts.k'] + copied_requires),
            imports=_imports,
        )

        kevm = KEVM(
            kdist.get('foundry'),
            extra_unparsing_modules=(bin_runtime_definition.all_modules + contract_main_definition.all_modules),
        )

        foundry_contracts_file.write_text(kevm.pretty_print(bin_runtime_definition, unalias=False) + '\n')
        _LOGGER.info(f'Wrote file: {foundry_contracts_file}')
        foundry.main_file.write_text(kevm.pretty_print(contract_main_definition) + '\n')
        _LOGGER.info(f'Wrote file: {foundry.main_file}')

    def kompilation_digest() -> str:
        k_files = list(requires) + [foundry_contracts_file, foundry.main_file]
        return hash_str(''.join([hash_str(Path(k_file).read_text()) for k_file in k_files]))

    def kompilation_up_to_date() -> bool:
        if not foundry.digest_file.exists():
            return False
        digest_dict = json.loads(foundry.digest_file.read_text())
        if 'kompilation' not in digest_dict:
            digest_dict['kompilation'] = ''
        foundry.digest_file.write_text(json.dumps(digest_dict, indent=4))
        return digest_dict['kompilation'] == kompilation_digest()

    def update_kompilation_digest() -> None:
        digest_dict = {}
        if foundry.digest_file.exists():
            digest_dict = json.loads(foundry.digest_file.read_text())
        digest_dict['kompilation'] = kompilation_digest()
        foundry.digest_file.write_text(json.dumps(digest_dict, indent=4))

        _LOGGER.info('Updated Kompilation digest')

    if not kompilation_up_to_date() or rekompile or not kompiled_timestamp.exists():
        plugin_dir = kdist.get('plugin')

        kevm_kompile(
            target=target,
            output_dir=foundry.kompiled,
            main_file=foundry.main_file,
            main_module=main_module,
            syntax_module=syntax_module,
            includes=includes,
            emit_json=True,
            ccopts=ccopts,
            llvm_library=foundry.llvm_library,
            debug=debug,
            verbose=verbose,
            plugin_dir=plugin_dir,
        )

    update_kompilation_digest()
    foundry.update_digest()


def _foundry_to_contract_def(
    empty_config: KInner,
    contracts: Iterable[Contract],
    requires: Iterable[str],
) -> KDefinition:
    modules = [contract_to_main_module(contract, empty_config, imports=['FOUNDRY']) for contract in contracts]
    # First module is chosen as main module arbitrarily, since the contract definition is just a set of
    # contract modules.
    main_module = Contract.contract_to_module_name(list(contracts)[0].name_upper)

    return KDefinition(
        main_module,
        modules,
        requires=(KRequire(req) for req in list(requires)),
    )


def _foundry_to_main_def(
    main_module: str,
    contracts: Iterable[Contract],
    empty_config: KInner,
    requires: Iterable[str],
    imports: dict[str, list[str]],
) -> KDefinition:
    modules = [
        contract_to_verification_module(contract, empty_config, imports=imports[contract.name])
        for contract in contracts
    ]
    _main_module = KFlatModule(
        main_module,
        imports=(KImport(mname) for mname in [_m.name for _m in modules]),
    )

    return KDefinition(
        main_module,
        [_main_module] + modules,
        requires=(KRequire(req) for req in list(requires)),
    )
