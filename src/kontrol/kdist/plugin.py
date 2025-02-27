from __future__ import annotations

from typing import TYPE_CHECKING

from kevm_pyk.kdist.plugin import KEVMTarget
from kevm_pyk.kompile import KompileTarget

from .utils import KSRC_DIR

if TYPE_CHECKING:
    from typing import Final


__TARGETS__: Final = {
    'base': KEVMTarget(
        {
            'target': KompileTarget.HASKELL,
            'main_file': KSRC_DIR / 'kontrol.md',
            'main_module': 'KONTROL-BASE',
            'syntax_module': 'KONTROL-BASE',
        },
    ),
    'kontrol-keccak': KEVMTarget(
        {
            'target': KompileTarget.HASKELL,
            'main_file': KSRC_DIR / 'kontrol.md',
            'main_module': 'KONTROL-KECCAK',
            'syntax_module': 'KONTROL-KECCAK',
        },
    ),
    'kontrol-aux': KEVMTarget(
        {
            'target': KompileTarget.HASKELL,
            'main_file': KSRC_DIR / 'kontrol.md',
            'main_module': 'KONTROL-AUX',
            'syntax_module': 'KONTROL-AUX',
        },
    ),
    'kontrol-full': KEVMTarget(
        {
            'target': KompileTarget.HASKELL,
            'main_file': KSRC_DIR / 'kontrol.md',
            'main_module': 'KONTROL-FULL',
            'syntax_module': 'KONTROL-FULL',
        },
    ),
}
