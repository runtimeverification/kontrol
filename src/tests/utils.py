from __future__ import annotations

from shutil import copytree
from typing import TYPE_CHECKING

from pyk.utils import run_process_2

from kontrol.foundry import Foundry

if TYPE_CHECKING:
    from typing import Final
    from pathlib import Path

from typing import TYPE_CHECKING

FORGE_STD_REF: Final = '75f1746'


def forge_build(test_data_dir: Path, target_dir: Path) -> Foundry:
    copytree(str(test_data_dir / 'foundry'), str(target_dir))
    run_process_2(['forge', 'install', '--no-git', f'foundry-rs/forge-std@{FORGE_STD_REF}'], cwd=target_dir)
    run_process_2(['forge', 'build'], cwd=target_dir)
    return Foundry(foundry_root=target_dir)
