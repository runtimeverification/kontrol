from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk.kompile import KompileTarget
from pyk.cli.args import Options
from pyk.cli.utils import dir_path

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from typing import Any, TypeVar

    T = TypeVar('T')


class FoundryOptions(Options):
    foundry_root: Path

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'foundry_root': Path('.'),
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--foundry-project-root',
            dest='foundry_root',
            type=dir_path,
            help='Path to Foundry project root directory.',
        )


class FoundryTestOptions(Options):
    test: str
    version: int | None

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'version': None,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument('test', type=str, help='Test to run')
        parser.add_argument('--version', type=int, required=False, help='Version of the test to use')


class KGenOptions(Options):
    requires: list[str]
    imports: list[str]

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'requires': [],
            'imports': [],
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--require',
            dest='requires',
            action='append',
            help='Extra K requires to include in generated output.',
        )
        parser.add_argument(
            '--module-import',
            dest='imports',
            action='append',
            help='Extra modules to import into generated main module.',
        )


class KompileTargetOptions(Options):
    target: KompileTarget

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'target': KompileTarget.HASKELL,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--target',
            type=KompileTarget,
            choices=[KompileTarget.HASKELL, KompileTarget.MAUDE],
            help='[haskell|maude]',
        )


class RPCOptions(Options):
    trace_rewrites: bool
    kore_rpc_command: str | None
    use_booster: bool
    port: int | None
    maude_port: int | None

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'trace_rewrites': False,
            'kore_rpc_command': None,
            'use_booster': True,
            'port': None,
            'maude_port': None,
        }

    @staticmethod
    def update_args(parser: ArgumentParser) -> None:
        parser.add_argument(
            '--trace-rewrites',
            dest='trace_rewrites',
            action='store_true',
            help='Log traces of all simplification and rewrite rule applications.',
        )
        parser.add_argument(
            '--kore-rpc-command',
            dest='kore_rpc_command',
            type=str,
            help='Custom command to start RPC server.',
        )
        parser.add_argument(
            '--use-booster',
            dest='use_booster',
            action='store_true',
            help='Use the booster RPC server instead of kore-rpc.',
        )
        parser.add_argument(
            '--no-use-booster',
            dest='use_booster',
            action='store_false',
            help='Do not use the booster RPC server instead of kore-rpc.',
        )
        parser.add_argument(
            '--port',
            dest='port',
            type=int,
            default=None,
            help='Use existing RPC server on named port.',
        )
        parser.add_argument(
            '--maude-port',
            dest='maude_port',
            type=int,
            default=None,
            help='Use existing Maude RPC server on named port.',
        )
