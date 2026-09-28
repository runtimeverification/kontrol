from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from pyk.proof.proof import Proof

import kontrol.foundry as foundry_module
from kontrol.foundry import Foundry

if TYPE_CHECKING:
    pass

    from _pytest.monkeypatch import MonkeyPatch  # Importing the type for annotation


def mock_listdir(_f: Foundry) -> list[str]:
    return [
        'test%AssertTest.test_assert_true():0',
        'test%AssertTest.setUp():0',
        'test%AssertTest.setUp():1',
        'long%path%to%test%DeeplyNestedTest.testWithMultipleVersions():0',
        'long%path%to%test%DeeplyNestedTest.testWithMultipleVersions():1',
        'long%path%to%test%DeeplyNestedTest.testWithMultipleVersions():2',
        'long%path%to%test%DeeplyNestedTest.testWithMultipleVersions():3',
    ]


TEST_ID_DATA: list[tuple[str, str, int | None]] = [
    (
        'single_version',
        'test%AssertTest.test_assert_true()',
        0,
    ),
    (
        'two_versions',
        'test%AssertTest.setUp()',
        1,
    ),
    (
        'deeply_nested_test',
        'long%path%to%test%DeeplyNestedTest.testWithMultipleVersions()',
        3,
    ),
    (
        'nonexistent_test',
        'test%AssertTest.test_assert_false()',
        None,
    ),
]


@pytest.mark.parametrize('test_id,test,expected_version', TEST_ID_DATA, ids=[test_id for test_id, *_ in TEST_ID_DATA])
def test_foundry_latest_proof_version(
    monkeypatch: MonkeyPatch, test_id: str, test: str, expected_version: int | None
) -> None:

    # Given
    monkeypatch.setattr(Foundry, '__init__', lambda _: None)
    monkeypatch.setattr(Foundry, 'list_proof_dir', mock_listdir)

    foundry = Foundry()  # type: ignore

    latest_version = foundry.latest_proof_version(test)

    # Then
    assert latest_version == expected_version


RESOLVE_PROOF_VERSION_DATA: list[tuple[str, int | None, int]] = [
    ('explicit_zero', 0, 0),
    ('explicit_nonzero', 2, 2),
    ('omitted', None, 3),
]


@pytest.mark.parametrize(
    'test_id,user_specified_version,expected_version',
    RESOLVE_PROOF_VERSION_DATA,
    ids=[test_id for test_id, *_ in RESOLVE_PROOF_VERSION_DATA],
)
def test_foundry_resolve_proof_version(
    monkeypatch: MonkeyPatch, test_id: str, user_specified_version: int | None, expected_version: int
) -> None:
    # Given
    test = 'long%path%to%test%DeeplyNestedTest.testWithMultipleVersions()'
    method = SimpleNamespace(up_to_date=lambda _digest_file: True)

    monkeypatch.setattr(Foundry, '__init__', lambda _: None)
    monkeypatch.setattr(Foundry, 'digest_file', Path('digest'))
    monkeypatch.setattr(Foundry, 'proofs_dir', Path('proofs'))
    monkeypatch.setattr(Foundry, 'list_proof_dir', mock_listdir)
    monkeypatch.setattr(Foundry, 'get_contract_and_method', lambda _self, _test: (None, method))
    monkeypatch.setattr(foundry_module, 'kontrol_up_to_date', lambda _digest_file: True)

    foundry = Foundry()  # type: ignore
    existing_proofs = mock_listdir(foundry)
    monkeypatch.setattr(Proof, 'proof_data_exists', lambda proof_id, _proofs_dir: proof_id in existing_proofs)

    # When
    version = foundry.resolve_proof_version(test, reinit=False, user_specified_version=user_specified_version)

    # Then
    assert version == expected_version
