from __future__ import annotations

from difflib import unified_diff
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pyk.proof import APRProof
from pyk.proof.reachability import APRFailureInfo

if TYPE_CHECKING:
    from typing import Final

    from pyk.proof.proof import Proof


TEST_DATA_DIR: Final = (Path(__file__).parent / 'test-data').resolve(strict=True)


def assert_or_update_show_output(actual_text: str, expected_file: Path, *, update: bool) -> None:
    if update:
        expected_file.write_text(actual_text)
    else:
        assert expected_file.is_file()
        expected_text = expected_file.read_text()
        if actual_text != expected_text:
            diff = '\n'.join(
                unified_diff(
                    expected_text.splitlines(),
                    actual_text.splitlines(),
                    fromfile=str(expected_file),
                    tofile='actual_text',
                    lineterm='',
                )
            )
            raise AssertionError(f'The actual output does not match the expected output:\n{diff}')


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
