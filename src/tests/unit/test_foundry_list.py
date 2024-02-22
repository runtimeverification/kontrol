from __future__ import annotations

from functools import cached_property
from os import listdir
from typing import TYPE_CHECKING, cast

import pytest
from pyk.proof.proof import Proof

from kontrol.foundry import Foundry, foundry_list
from kontrol.solc_to_k import Contract

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Final


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
            contract.contract_path = contract._name
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


PROOF_ID_DATA: list[tuple[str, str, list[str], list[str]]] = [
    (
        'common_case',
        'AssertTest.setUp',
        [
            'test%AssertTest.setUp():0',
            'test_1%test_2%ContractName.functionName(uint256):1',
            'test_1%ContractName:functionName():0',
        ],
        ['test%AssertTest.setUp():0'],
    ),
    (
        'nested_case',
        'functionName',
        [
            'test%AssertTest.setUp():0',
            'test_1%test_2%ContractName.functionName(uint256):1',
            'test_1%ContractName:functionName():0',
            'OtherContract.functionName(string):0',
        ],
        ['test_1%test_2%ContractName.functionName(uint256):1'],
    ),
]


@pytest.mark.parametrize(
    'test_id,test_name,proof_ids,expected', PROOF_ID_DATA, ids=[test_id for test_id, *_ in PROOF_ID_DATA]
)
def test_proof_identification(test_id: str, test_name: str, proof_ids: list[str], expected: list[str]) -> None:

    # When
    actual = Foundry.filter_proof_ids(proof_ids, test_name)

    # Then
    assert actual == expected
