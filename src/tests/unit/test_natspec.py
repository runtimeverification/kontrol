from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pyk.kast.prelude.kint import intToken
from sgp.ast_node_types import NumberLiteral  # type: ignore

from kontrol.natspec import handle_numerical_literal

if TYPE_CHECKING:
    from typing import Final

    from pyk.kast.inner import KToken

TEST_DATA: Final = {
    ('base-number', NumberLiteral('100'), intToken(100)),
    ('scientific-number', NumberLiteral('1e18'), intToken(int(1e18))),
    ('scientific-number-denomination', NumberLiteral('1e11', 'days'), intToken(8640000000000000)),
    ('decimal-point', NumberLiteral('0.85', 'ether'), intToken(int(85 * 1e16))),
    ('decimal-point-without-denomination', NumberLiteral('0.78'), None),
    ('hexadecimal', NumberLiteral('0xff'), intToken(255)),
    ('hexadecimal-with-denomination', NumberLiteral('0xff', 'gwei'), None),
}


@pytest.mark.parametrize('test_id,input,expected', TEST_DATA, ids=[test_id for test_id, *_ in TEST_DATA])
def test_handle_numerical_literal(test_id: str, input: NumberLiteral, expected: KToken | None) -> None:
    output = handle_numerical_literal(input)
    assert output == expected
