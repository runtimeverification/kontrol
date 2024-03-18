from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

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
