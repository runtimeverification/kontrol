from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from pyk.kbuild.utils import k_version
from pyk.kdist.api import Target
from pyk.ktool.kompile import PykBackend, kompile

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any, Final
    from pathlib import Path

from .utils import KSRC_DIR


class SourceTarget(Target):

    def build(self, output_dir: Path, deps: dict[str, Path], args: dict[str, Any], verbose: bool) -> None:
        shutil.copy(KSRC_DIR / 'natspec-grammar.md', output_dir / 'natspec-grammar.md')

    def source(self) -> tuple[Path, ...]:
        return (KSRC_DIR,)


class KompileTarget(Target):
    _kompile_args: Callable[[Path], Mapping[str, Any]]

    def __init__(self, kompile_args: Callable[[Path], Mapping[str, Any]]):
        self._kompile_args = kompile_args

    def build(self, output_dir: Path, deps: dict[str, Path], args: dict[str, Any], verbose: bool) -> None:
        kompile_args = self._kompile_args(deps['natspec.source'])
        kompile(output_dir=output_dir, verbose=verbose, **kompile_args)

    def context(self) -> dict[str, str]:
        return {'k-version': k_version().text}

    def deps(self) -> tuple[str]:
        return ('natspec.source',)


__TARGETS__: Final = {
    'source': SourceTarget(),
    'llvm': KompileTarget(
        lambda src_dir: {
            'backend': PykBackend.LLVM,
            'main_file': src_dir / 'natspec-grammar.md',
            'main_module': 'NATSPEC',
            'syntax_module': 'NATSPEC-SYNTAX',
            'md_selector': 'k',
            'warnings_to_errors': True,
            'gen_glr_bison_parser': True,
            'opt_level': 3,
            'ccopts': ['-g'],
        },
    ),
}
