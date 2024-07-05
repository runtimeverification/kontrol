from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pyk.proof import APRProof
from pyk.proof.reachability import APRFailureInfo
from pyk.utils import check_dir_path

from kontrol.options import SolcToKOptions
from kontrol.solc_to_k import solc_to_k

if TYPE_CHECKING:
    from typing import Final

    from pyk.proof.proof import Proof


TEST_DATA_DIR: Final = (Path(__file__).parent / 'test-data').resolve(strict=True)


def gen_bin_runtime(contract_file: Path, output_dir: Path) -> tuple[Path, str]:
    check_dir_path(output_dir)

    contract_name = contract_file.stem
    main_module_name = f'{contract_name.upper()}-VERIFICATION'
    main_file = output_dir / f'{contract_name.lower()}-bin-runtime.k'

    k_text = solc_to_k(
        SolcToKOptions(
            {
                'contract_file': contract_file,
                'contract_name': contract_name,
                'main_module': main_module_name,
            }
        )
    )

    main_file.write_text(k_text)
    return main_file, main_module_name


def assert_or_update_show_output(actual_text: str, expected_file: Path, *, update: bool) -> None:
    if update:
        expected_file.write_text(actual_text)
    else:
        assert expected_file.is_file()
        expected_text = expected_file.read_text()
        assert actual_text == expected_text


def assert_pass(test: str, proof: Proof) -> None:
    if not proof.passed:
        if isinstance(proof, APRProof):
            assert proof.failure_info
            assert isinstance(proof.failure_info, APRFailureInfo)
            pytest.fail('\n'.join(proof.failure_info.print()))
        else:
            pytest.fail()


def assert_fail(test: str, proof: Proof) -> None:
    assert not proof.passed
    if isinstance(proof, APRProof):
        assert proof.failure_info
