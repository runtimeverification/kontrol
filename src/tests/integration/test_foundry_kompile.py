from __future__ import annotations

from typing import TYPE_CHECKING

from pyk.kast.inner import KApply
from pyk.kast.prelude.kint import intToken
from pyk.kore.rpc import KoreClient, kore_server

from kontrol.foundry import Foundry
from kontrol.kompile import foundry_kompile
from kontrol.options import BuildOptions

if TYPE_CHECKING:
    from pathlib import Path

    from pyk.kast.inner import KInner


def _lemma_value(foundry: Foundry) -> KInner:
    kevm = foundry.kevm
    with kore_server(definition_dir=foundry.kompiled, module_name=kevm.main_module) as server:
        with KoreClient('localhost', server.port) as client:
            result = client.simplify(kevm.kast_to_kore(KApply('lemmaValue')))
            return kevm.kore_to_kast(result.state)


def test_foundry_kompile_updated_lemma(tmp_path: Path) -> None:
    (tmp_path / 'foundry.toml').write_text('[profile.default]\nout = "out"\nsolc_version = "0.8.13"\n')
    (tmp_path / 'src').mkdir()
    contract = tmp_path / 'src' / 'LemmaTest.sol'
    contract.write_text('pragma solidity ^0.8.13;\ncontract LemmaTest {}\n')
    lemma = tmp_path / 'lemmas.k'
    lemma.write_text(
        'module LEMMA-UPDATE-TEST\n'
        '  imports INT\n'
        '  syntax Int ::= "lemmaValue" [function, klabel(lemmaValue), symbol]\n'
        '  rule lemmaValue => 0\n'
        'endmodule\n'
    )
    options = {'requires': [lemma.name], 'imports': ['LemmaTest:LEMMA-UPDATE-TEST'], 'o2': False}
    foundry = Foundry(tmp_path)
    foundry_kompile(BuildOptions(options), foundry)
    assert _lemma_value(foundry) == intToken(0)

    lemma.write_text(lemma.read_text().replace('=> 0', '=> 1'))
    foundry = Foundry(tmp_path)
    foundry_kompile(BuildOptions(options), foundry)
    assert _lemma_value(foundry) == intToken(1)

    timestamp = foundry.kompiled / 'timestamp'
    original_mtime = timestamp.stat().st_mtime_ns
    foundry_kompile(BuildOptions(options), Foundry(tmp_path))
    assert timestamp.stat().st_mtime_ns == original_mtime

    contract.write_text(
        'pragma solidity ^0.8.13;\n'
        'contract LemmaTest { function value() public pure returns (uint256) { return 1; } }\n'
    )
    foundry_kompile(BuildOptions(options), Foundry(tmp_path))
    assert timestamp.stat().st_mtime_ns == original_mtime
