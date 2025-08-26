from __future__ import annotations

import logging
import os
from subprocess import run
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from pyk.kore.parser import KoreParser
from pyk.ktool.kprint import KPrint

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path
    from typing import Final

    from pyk.kast.inner import KInner
    from pyk.kast.outer import KFlatModule
    from pyk.kore.parser import Pattern
    from pyk.ktool.kprint import SymbolTable
    from pyk.utils import BugReport

_LOGGER: Final = logging.getLogger(__name__)


class Natspec(KPrint):
    _parser_executable: Path

    def __init__(
        self,
        definition_dir: Path,
        use_directory: Path | None = None,
        bug_report: BugReport | None = None,
        extra_unparsing_modules: Iterable[KFlatModule] = (),
        patch_symbol_table: Callable[[SymbolTable], None] | None = None,
    ) -> None:

        KPrint.__init__(
            self,
            definition_dir=definition_dir,
            use_directory=use_directory,
            bug_report=bug_report,
            extra_unparsing_modules=extra_unparsing_modules,
            patch_symbol_table=patch_symbol_table,
        )
        print(definition_dir)
        self._parser_executable = definition_dir / 'parser_PGM'

    def _run_parser(self, input: str) -> Pattern:
        _LOGGER.debug(f'Running parser_PGM for: {input}')
        with NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(input)
            temp_path = f.name

        try:
            result = run(
                [self._parser_executable, temp_path],
                capture_output=True,
                text=True,
                check=True,
            )
            kore = KoreParser(result.stdout).pattern()
            return kore
        finally:
            os.unlink(temp_path)

    def decode(self, input: str) -> KInner:
        kore_pattern = self._run_parser(input)
        return self.kore_to_kast(kore_pattern)
