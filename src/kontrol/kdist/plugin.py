from __future__ import annotations

from typing import TYPE_CHECKING

from kevm_pyk.kdist.plugin import KEVMTarget
from kevm_pyk.kompile import KompileTarget

from .utils import KSRC_DIR

if TYPE_CHECKING:
    from typing import Final


__TARGETS__: Final = {
    'foundry': KEVMTarget(
        {
            'target': KompileTarget.HASKELL,
            'main_file': KSRC_DIR / 'vm.md',
            'main_module': 'KONTROL-VM',
            'syntax_module': 'KONTROL-VM',
        },
    ),
}

# 'main_file': KSRC_DIR / 'foundry.md',