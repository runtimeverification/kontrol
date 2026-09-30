from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import pytest
from pyk.kast.pretty import PrettyPrinter

from kontrol.foundry import Foundry
from kontrol.kompile import foundry_kompile
from kontrol.options import BuildOptions

if TYPE_CHECKING:
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.fixture
def project(tmp_path: Path, mocker: MockerFixture) -> tuple[Foundry, Path, MagicMock]:
    (tmp_path / 'foundry.toml').write_text('[profile.default]\nout = "out"\n')
    lemma = tmp_path / 'lemmas.k'
    lemma.write_text('module LEMMA-UPDATE-TEST\n  imports INT\n  rule 0 +Int X => X [simplification]\nendmodule\n')
    foundry = Foundry(tmp_path)
    mocker.patch('kontrol.kompile.kdist').get.return_value = tmp_path
    kevm = mocker.patch('kontrol.kompile.KEVM')
    kevm.return_value.pretty_print.side_effect = lambda definition: PrettyPrinter(definition).print(definition)
    compiler = mocker.patch('kontrol.kompile.kevm_kompile')
    compiler.side_effect = lambda **_kwargs: (foundry.kompiled / 'timestamp').touch()
    foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)
    compiler.reset_mock()
    return foundry, lemma, compiler


def test_foundry_kompile_updated_lemma(project: tuple[Foundry, Path, MagicMock]) -> None:
    foundry, lemma, compiler = project
    original_digest = foundry.digest_file.read_bytes()
    original_stat = lemma.stat()
    lemma.write_text(lemma.read_text().replace('0 +Int X', 'X +Int 0'))
    os.utime(lemma, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    copied_lemma = foundry.kompiled / 'requires' / lemma.name
    compiled_lemmas: list[bytes] = []

    def compile_lemma(**_kwargs: object) -> None:
        compiled_lemmas.append(copied_lemma.read_bytes())
        (foundry.kompiled / 'timestamp').touch()

    compiler.side_effect = compile_lemma
    foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)

    assert compiled_lemmas == [lemma.read_bytes()]
    assert foundry.digest_file.read_bytes() != original_digest
    compiler.reset_mock()
    foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)
    compiler.assert_not_called()


def test_foundry_kompile_stale_copy(project: tuple[Foundry, Path, MagicMock]) -> None:
    foundry, lemma, compiler = project
    copied_lemma = foundry.kompiled / 'requires' / lemma.name
    copied_lemma.write_text(lemma.read_text().replace('0 +Int X', 'X +Int 0'))
    original_digest = foundry.digest_file.read_bytes()

    foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)

    compiler.assert_called_once()
    assert copied_lemma.read_bytes() == lemma.read_bytes()
    assert foundry.digest_file.read_bytes() == original_digest


def test_foundry_kompile_unchanged_lemma(project: tuple[Foundry, Path, MagicMock]) -> None:
    foundry, lemma, compiler = project
    copied_lemma = foundry.kompiled / 'requires' / lemma.name
    original_mtime = copied_lemma.stat().st_mtime_ns
    original_digest = foundry.digest_file.read_bytes()

    foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)

    compiler.assert_not_called()
    assert copied_lemma.stat().st_mtime_ns == original_mtime
    assert foundry.digest_file.read_bytes() == original_digest


@pytest.mark.parametrize('stale_copy', [False, True], ids=['source-edit', 'stale-copy'])
def test_foundry_kompile_failed_retry(project: tuple[Foundry, Path, MagicMock], stale_copy: bool) -> None:
    foundry, lemma, compiler = project
    copied_lemma = foundry.kompiled / 'requires' / lemma.name
    changed_file = copied_lemma if stale_copy else lemma
    changed_file.write_text(changed_file.read_text().replace('0 +Int X', 'X +Int 0'))
    original_digest = foundry.digest_file.read_bytes()
    timestamp = foundry.kompiled / 'timestamp'

    def fail_compile(**_kwargs: object) -> None:
        assert not timestamp.exists()
        timestamp.touch()  # Simulate one backend completing before the other fails.
        raise RuntimeError('kompilation failed')

    compiler.side_effect = fail_compile
    with pytest.raises(RuntimeError, match='kompilation failed'):
        foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)

    assert foundry.digest_file.read_bytes() == original_digest
    assert not timestamp.exists()
    compiler.reset_mock()
    compiler.side_effect = lambda **_kwargs: timestamp.touch()
    foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)
    compiler.assert_called_once()
    assert copied_lemma.read_bytes() == lemma.read_bytes()
    assert timestamp.exists()


def test_foundry_kompile_missing_copy(project: tuple[Foundry, Path, MagicMock]) -> None:
    foundry, lemma, compiler = project
    copied_lemma = foundry.kompiled / 'requires' / lemma.name
    copied_lemma.unlink()

    foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)

    compiler.assert_called_once()
    assert copied_lemma.read_bytes() == lemma.read_bytes()


def test_foundry_kompile_contract_digest_change(project: tuple[Foundry, Path, MagicMock]) -> None:
    foundry, lemma, compiler = project
    digest = json.loads(foundry.digest_file.read_text())
    digest['foundry'] = 'old-contract-digest'
    foundry.digest_file.write_text(json.dumps(digest))

    foundry_kompile(BuildOptions({'requires': [lemma.name], 'forge_build': False}), foundry)

    compiler.assert_not_called()
    assert foundry.up_to_date()
