from __future__ import annotations

from functools import cached_property
from typing import cast

import pytest

from kontrol.foundry import Foundry


class FoundryMock:

    @cached_property
    def all_tests(self) -> list[str]:
        return [
            'test%AssertTest.checkFail_assert_false()',
            'test%AssertTest.test_assert_false()',
            'test%AssertTest.test_assert_true()',
            'test%AssertTest.testFail_assert_true()',
        ]

    @cached_property
    def all_non_tests(self) -> list[str]:
        return ['test%AssertTest.setUp()']

    # NOTE: Hardcoded list of proofs used to mock Foundry.proof_ids_with_test()
    @cached_property
    def proof_ids(self) -> list[str]:
        return [
            'test%AssertTest.checkFail_assert_false():0',
            'test%AssertTest.test_assert_false():0',
            'test%AssertTest.test_assert_true():0',
            'test%AssertTest.testFail_assert_true():0',
            'test%AssertTest.setUp():0',
            'test%AssertTest.setUp():1',
        ]

    def proof_ids_with_test(self, test: str, version: int | None = None) -> list[str]:
        return Foundry.filter_proof_ids(self.proof_ids, test, version)

    def matching_sigs(self, test: str) -> list[str]:
        foundry = cast('Foundry', self)
        return Foundry.matching_tests(foundry, [test])

    def get_test_id(self, test: str, version: int | None) -> str:
        foundry = cast('Foundry', self)
        return Foundry.get_test_id(foundry, test, version)

    # NOTE: hardcoded method required to mock Foundry.get_test_id().
    # NOTE: It finds 1 as the highest version of any proof.
    def resolve_proof_version(
        self,
        test: str,
        reinit: bool,
        user_specified_version: int | None,
    ) -> int:
        return 1


TEST_ID_DATA = [
    (
        'with_version',
        'AssertTest.setUp()',
        0,
        'test%AssertTest.setUp():0',
    ),
    (
        'without_version',
        'AssertTest.setUp()',
        None,
        'test%AssertTest.setUp():1',
    ),
]


@pytest.mark.parametrize('test_id,test,version,expected', TEST_ID_DATA, ids=[test_id for test_id, *_ in TEST_ID_DATA])
def test_foundry_get_test_id(test_id: str, test: str, version: int | None, expected: str) -> None:

    # Given
    foundry = cast('Foundry', FoundryMock())

    # When
    id = foundry.get_test_id(test, version)

    # Then
    assert id == expected
