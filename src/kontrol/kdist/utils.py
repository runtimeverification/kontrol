from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final


KSRC_DIR: Final = Path(__file__).parent.resolve(strict=True)
