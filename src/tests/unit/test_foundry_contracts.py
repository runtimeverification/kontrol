from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from kontrol.foundry import Foundry

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    'second_path,second_name,expected',
    [
        ('test/CounterFuzz.t.sol', 'CounterTest', None),
        ('other/CounterFuzz.t.sol', 'CounterTest', ['other%CounterTest', 'test%CounterTest']),
        ('test/CounterFuzz.t.sol', 'OtherTest', ['test%CounterTest', 'test%OtherTest']),
    ],
)
def test_contract_artifact_names(
    tmp_path: Path, second_path: str, second_name: str, expected: list[str] | None
) -> None:
    (tmp_path / 'foundry.toml').write_text('[profile.default]\nout = "out"\n')
    for source_path, name in [('test/Counter.t.sol', 'CounterTest'), (second_path, second_name)]:
        artifact_dir = tmp_path / 'out' / source_path.split('/')[-1]
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / f'{name}.json').write_text(
            json.dumps(
                {
                    'id': 0,
                    'ast': {'absolutePath': source_path, 'nodes': []},
                    'bytecode': {'object': '0x'},
                    'deployedBytecode': {'object': '0x'},
                    'abi': [],
                }
            )
        )
    foundry = Foundry(tmp_path)
    if expected is None:
        with pytest.raises(ValueError, match='Duplicate contract identifier test%CounterTest') as error:
            _ = foundry.contracts
        assert all(path in str(error.value) for path in ['test/Counter.t.sol', second_path])
    else:
        assert sorted(foundry.contracts) == expected
