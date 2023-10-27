from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk.kdist.plugin import KEVMTarget
from kevm_pyk.kompile import KompileTarget

if TYPE_CHECKING:
    from typing import Final


FOUNDRY_MD_FILE: Final = Path(__file__).parent / 'foundry.md'


__TARGETS__: Final = {
    'foundryx': KEVMTarget(
        {
            'target': KompileTarget.HASKELL,
            'main_file': FOUNDRY_MD_FILE,
            'main_module': 'FOUNDRY',
            'syntax_module': 'FOUNDRY',
        },
    ),
}
