from __future__ import annotations

from argparse import ArgumentParser
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk.cli import KEVMCLIArgs
from pyk.cli.utils import dir_path

if TYPE_CHECKING:
    from typing import TypeVar

    T = TypeVar('T')


class KontrolCLIArgs(KEVMCLIArgs):
    @cached_property
    def foundry_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--foundry-project-root',
            dest='foundry_root',
            type=dir_path,
            default=Path('.'),
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
    def rpc_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--trace-rewrites',
            dest='trace_rewrites',
            default=False,
            action='store_true',
            help='Log traces of all simplification and rewrite rule applications.',
        )
        args.add_argument(
            '--kore-rpc-command',
            dest='kore_rpc_command',
            type=str,
            default=None,
            help='Custom command to start RPC server',
        )
        args.add_argument(
            '--use-booster',
            dest='use_booster',
            default=False,
            action='store_true',
            help="Use the booster RPC server instead of kore-rpc.",
        )
        return args
