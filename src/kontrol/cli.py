from __future__ import annotations

from argparse import ArgumentParser
from functools import cached_property
from typing import TYPE_CHECKING, Any

from kevm_pyk.cli import KEVMCLIArgs
from kevm_pyk.kompile import KompileTarget
from pyk.cli.utils import dir_path

from .options import (
    BuildOptions,
    CleanOptions,
    CompileOptions,
    GetModelOptions,
    InitOptions,
    ListOptions,
    LoadStateDiffOptions,
    MergeNodesOptions,
    MinimizeProofOptions,
    ProveOptions,
    RefuteNodeOptions,
    RemoveNodeOptions,
    SectionEdgeOptions,
    ShowOptions,
    SimplifyNodeOptions,
    SolcToKOptions,
    SplitNodeOptions,
    StepNodeOptions,
    ToDotOptions,
    UnrefuteNodeOptions,
    VersionOptions,
    ViewKcfgOptions,
)

if TYPE_CHECKING:
    from typing import TypeVar

    from .options import LoggingOptions

    T = TypeVar('T')


def generate_options(args: dict[str, Any]) -> LoggingOptions:
    command = args['command']
    options = {
        'load-state-diff': LoadStateDiffOptions(args),
        'version': VersionOptions(args),
        'compile': CompileOptions(args),
        'solc-to-k': SolcToKOptions(args),
        'build': BuildOptions(args),
        'prove': ProveOptions(args),
        'show': ShowOptions(args),
        'refute-node': RefuteNodeOptions(args),
        'unrefute-node': UnrefuteNodeOptions(args),
        'split-node': SplitNodeOptions(args),
        'to-dot': ToDotOptions(args),
        'list': ListOptions(args),
        'view-kcfg': ViewKcfgOptions(args),
        'remove-node': RemoveNodeOptions(args),
        'simplify-node': SimplifyNodeOptions(args),
        'step-node': StepNodeOptions(args),
        'merge-nodes': MergeNodesOptions(args),
        'section-edge': SectionEdgeOptions(args),
        'get-model': GetModelOptions(args),
        'minimize-proof': MinimizeProofOptions(args),
        'clean': CleanOptions(args),
        'init': InitOptions(args),
    }
    try:
        return options[command]
    except KeyError as err:
        raise ValueError(f'Unrecognized command: {command}') from err


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
