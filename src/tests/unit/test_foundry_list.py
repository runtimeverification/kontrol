from __future__ import annotations

from functools import cached_property
from os import listdir
from typing import TYPE_CHECKING, cast

from pyk.proof.proof import Proof

from kontrol.foundry import foundry_list
from kontrol.solc_to_k import Contract

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final

    from kontrol.foundry import Foundry


LIST_DATA_DIR: Final = TEST_DATA_DIR / 'foundry-list'
LIST_APR_PROOF: Final = LIST_DATA_DIR / 'apr_proofs'
LIST_EXPECTED: Final = LIST_DATA_DIR / 'foundry-list.expected'


class FoundryMock:
    @property
    def proofs_dir(self) -> Path:
        return LIST_DATA_DIR / 'apr_proofs'

    @cached_property
    def contracts(self) -> dict[str, Contract]:
        ret: dict[str, Contract] = {}
        for full_method in listdir(LIST_APR_PROOF):
            contract = Contract.__new__(Contract)
            method = Contract.Method.__new__(Contract.Method)
            contract_method, *_ = full_method.split(':')
            contract._name, method.signature = contract_method.split('.')
            if not hasattr(contract, 'methods'):
                contract.methods = ()
            contract.methods = contract.methods + (method,)
            ret[full_method] = contract
        return ret

    def get_optional_proof(self, test_id: str) -> Proof | None:
        return Proof.read_proof_data(LIST_APR_PROOF, test_id)


def test_foundry_list(update_expected_output: bool) -> None:
    # Given
    foundry = cast('Foundry', FoundryMock())
    expected = LIST_EXPECTED.read_text()

    # When
    actual = '\n'.join(foundry_list(foundry))

    # Then
    if update_expected_output:
        LIST_EXPECTED.write_text(actual)
        return

    assert actual == expected
