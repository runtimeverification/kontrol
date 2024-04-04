from __future__ import annotations

from argparse import ArgumentParser
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kevm_pyk.cli import KEVMCLIArgs
from kevm_pyk.kompile import KompileTarget
from pyk.cli.args import Options
from pyk.cli.utils import dir_path

if TYPE_CHECKING:
    from typing import TypeVar

    T = TypeVar('T')


class FoundryOptions(Options):
    foundry_root: Path

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'foundry_root': Path('.'),
        }


class FoundryTestOptions(Options):
    test: str
    version: int | None

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'version': None,
        }


class KGenOptions(Options):
    requires: list[str]
    imports: list[str]

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'requires': [],
            'imports': [],
        }


class KompileTargetOptions(Options):
    target: KompileTarget

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'target': KompileTarget.HASKELL,
        }


class TraceOptions(Options):
    active_tracing: bool
    trace_storage: bool
    trace_wordstack: bool
    trace_memory: bool

    @staticmethod
    def default() -> dict[str, Any]:
        return {
            'active_tracing': False,
            'trace_storage': False,
            'trace_wordstack': False,
            'trace_memory': False,
        }


class RpcOptions(Options):
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


class KontrolCLIArgs(KEVMCLIArgs):
    @cached_property
    def foundry_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--foundry-project-root',
            dest='foundry_root',
            type=dir_path,
            help='Path to Foundry project root directory.',
        )
        return args

    @cached_property
    def foundry_test_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument('test', type=str, help='Test to run')
        args.add_argument('--version', type=int, default=None, required=False, help='Version of the test to use')
        return args

    @cached_property
    def k_gen_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--require',
            dest='requires',
            default=[],
            action='append',
            help='Extra K requires to include in generated output.',
        )
        args.add_argument(
            '--module-import',
            dest='imports',
            default=[],
            action='append',
            help='Extra modules to import into generated main module.',
        )
        return args

    @cached_property
    def kompile_target_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--target',
            type=KompileTarget,
            choices=[KompileTarget.HASKELL, KompileTarget.MAUDE],
            help='[haskell|maude]',
        )
        return args

    @cached_property
    def rpc_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--trace-rewrites',
            dest='trace_rewrites',
            default=None,
            action='store_true',
            help='Log traces of all simplification and rewrite rule applications.',
        )
        args.add_argument(
            '--kore-rpc-command',
            dest='kore_rpc_command',
            type=str,
            help='Custom command to start RPC server.',
        )
        args.add_argument(
            '--use-booster',
            dest='use_booster',
            default=None,
            action='store_true',
            help='Use the booster RPC server instead of kore-rpc (default).',
        )
        args.add_argument(
            '--no-use-booster',
            dest='use_booster',
            default=None,
            action='store_false',
            help='Do not use the booster RPC server instead of kore-rpc.',
        )
        args.add_argument(
            '--port',
            dest='port',
            type=int,
            help='Use existing RPC server on named port.',
        )
        args.add_argument(
            '--maude-port',
            dest='maude_port',
            type=int,
            help='Use existing Maude RPC server on named port.',
        )
        return args
