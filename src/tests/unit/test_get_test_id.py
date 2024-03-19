from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kontrol.foundry import Foundry

if TYPE_CHECKING:
    pass

    from _pytest.monkeypatch import MonkeyPatch  # Importing the type for annotation


def mock_listdir(_f: Foundry) -> list[str]:
    return [
        'test%AssertTest.checkFail_assert_false():0',
        'test%AssertTest.test_assert_false():0',
        'test%AssertTest.test_assert_true():0',
        'test%AssertTest.testFail_assert_true():0',
        'test%AssertTest.setUp():0',
        'test%AssertTest.setUp():1',
    ]


def mock_all_tests() -> list[str]:
    return [
        'test%AssertTest.checkFail_assert_false()',
        'test%AssertTest.test_assert_false()',
        'test%AssertTest.test_assert_true()',
        'test%AssertTest.testFail_assert_true()',
    ]


def mock_all_non_tests() -> list[str]:
    return ['test%AssertTest.setUp()']


TEST_ID_DATA: list[tuple[str, str, int | None, bool, str]] = [
    (
        'with_version',
        'AssertTest.setUp()',
        0,
        False,
        'test%AssertTest.setUp():0',
    ),
    (
        'without_version',
        'AssertTest.setUp()',
        None,
        False,
        'test%AssertTest.setUp():1',
    ),
    (
        'no_matches',
        'AssertTest.setUp()',
        3,
        True,
        r'Found no matching proofs for AssertTest\.setUp\(\):3\.',
    ),
    (
        'multiple_matches_with_version',
        'AssertTest.test_assert',
        0,
        True,
        r'Found 2 matching proofs for AssertTest\.test_assert:0\.',
    ),
    (
        'multiple_matches_without_version',
        'AssertTest.test_assert',
        None,
        True,
        r'Found 2 matching proofs for AssertTest\.test_assert:None\.',
    ),
]


@pytest.mark.parametrize(
    'test_id,test,version,expect_error,expected_str', TEST_ID_DATA, ids=[test_id for test_id, *_ in TEST_ID_DATA]
)
def test_foundry_get_test_id(
    monkeypatch: MonkeyPatch, test_id: str, test: str, version: int | None, expect_error: bool, expected_str: str
) -> None:
    # Given
    monkeypatch.setattr(Foundry, '__init__', lambda _: None)
    monkeypatch.setattr(Foundry, 'list_proof_dir', mock_listdir)
    monkeypatch.setattr(Foundry, 'all_tests', mock_all_tests())
    monkeypatch.setattr(Foundry, 'all_non_tests', mock_all_non_tests())
    monkeypatch.setattr(Foundry, 'resolve_proof_version', lambda _self, _test, _reinit, _skip_setup_reinit, _version: 1)

    foundry = Foundry()  # type: ignore

    if expect_error:
        # When/Then
        with pytest.raises(ValueError, match=expected_str):
            foundry.get_test_id(test, version)
    else:
        # When
        id = foundry.get_test_id(test, version)

        # Then
        assert id == expected_str
