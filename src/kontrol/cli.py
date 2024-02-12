from __future__ import annotations

from argparse import ArgumentParser
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

from kevm_pyk.cli import KEVMCLIArgs
from kevm_pyk.kompile import KompileTarget
from pyk.cli.utils import dir_path, file_path

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
    def config_args(self) -> ArgumentParser:
        args = ArgumentParser(add_help=False)
        args.add_argument(
            '--config',
            dest='config_file',
            type=file_path,
            default=Path('./kontrol.toml'),
            help='Path to kontrol config file.',
        )
        args.add_argument(
            '--config-profile',
            dest='config_profile',
            default='default',
            help='Config profile to be used.',
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
            default=False,
            action='store_true',
            help='Log traces of all simplification and rewrite rule applications.',
        )
        args.add_argument(
            '--kore-rpc-command',
            dest='kore_rpc_command',
            type=str,
            default=None,
            help='Custom command to start RPC server.',
        )
        args.add_argument(
            '--use-booster',
            dest='use_booster',
            default=True,
            action='store_true',
            help='Use the booster RPC server instead of kore-rpc.',
        )
        args.add_argument(
            '--no-use-booster',
            dest='use_booster',
            action='store_false',
            help='Do not use the booster RPC server instead of kore-rpc.',
        )
        args.add_argument(
            '--port',
            dest='port',
            type=int,
            default=None,
            help='Use existing RPC server on named port.',
        )
        args.add_argument(
            '--maude-port',
            dest='maude_port',
            type=int,
            default=None,
            help='Use existing Maude RPC server on named port.',
        )
        return args
