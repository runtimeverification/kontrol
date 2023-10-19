from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk import kdist
from pyk.utils import check_dir_path

from kontrol.solc_to_k import solc_to_k

if TYPE_CHECKING:
    from typing import Final


TEST_DATA_DIR: Final = (Path(__file__).parent / 'test-data').resolve(strict=True)


def gen_bin_runtime(contract_file: Path, output_dir: Path) -> tuple[Path, str]:
    check_dir_path(output_dir)

    contract_name = contract_file.stem
    main_module_name = f'{contract_name.upper()}-VERIFICATION'
    main_file = output_dir / f'{contract_name.lower()}-bin-runtime.k'

    k_text = solc_to_k(
        definition_dir=kdist.get('haskell'),
        contract_file=contract_file,
        contract_name=contract_name,
        main_module=main_module_name,
    )

    main_file.write_text(k_text)
    return main_file, main_module_name
