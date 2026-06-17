from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from pyk.cli.pyk import parse_toml_args
from pyk.cterm.symbolic import HASKELL_LOGGING_ENTRIES

from kontrol.__main__ import _parse_toml_args
from kontrol.cli import (
    _create_argument_parser,
    generate_options,
    get_argument_type_setter,
    get_option_string_destination,
)
from kontrol.options import ProveOptions

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from typing import Final


TEST_TOML: Final = TEST_DATA_DIR / 'kontrol_test.toml'


def test_optionless_command() -> None:
    parser = _create_argument_parser()
    args = parser.parse_args(['version'])
    assert hasattr(args, 'config_file') == False
    assert args.command == 'version'


def test_continue_when_toml_absent() -> None:
    parser = _create_argument_parser()
    cmd_args = ['build', '--foundry-project-root', '.']
    args = parser.parse_args(cmd_args)
    assert hasattr(args, 'config_file')
    assert args.config_file == None
    args.config_file = Path('kontrol.toml')
    assert hasattr(args, 'config_profile')
    assert str(args.config_profile) == 'default'
    args_dict = parse_toml_args(args, get_option_string_destination, get_argument_type_setter)
    assert len(args_dict) == 0


def test_toml_read() -> None:
    parser = _create_argument_parser()
    cmd_args = ['build', '--config-file', str(TEST_TOML)]
    args = parser.parse_args(cmd_args)
    args_dict = parse_toml_args(args, get_option_string_destination, get_argument_type_setter)
    assert 'verbose' in args_dict
    assert not args_dict['verbose']
    assert 'debug' in args_dict
    assert not args_dict['debug']


def test_toml_read_default_profile() -> None:
    parser = _create_argument_parser()
    cmd_args = ['show', '--config-file', str(TEST_TOML), 'some_test']
    args = parser.parse_args(cmd_args)
    args_dict = parse_toml_args(args, get_option_string_destination, get_argument_type_setter)
    assert 'verbose' in args_dict
    assert args_dict['verbose']
    assert 'debug' in args_dict
    assert args_dict['verbose']
    assert 'version' in args_dict
    assert args_dict['version'] == 3
    assert 'node_deltas' in args_dict
    assert len(args_dict['node_deltas']) == 1


def test_cli_overrides_toml() -> None:
    parser = _create_argument_parser()
    cmd_args = ['build', '--config-file', str(TEST_TOML), '--foundry-project-root', str(TEST_TOML.parents[0])]
    args = parser.parse_args(cmd_args)
    args_dict = parse_toml_args(args, get_option_string_destination, get_argument_type_setter)
    stripped_args = args_dict | {
        key: val for (key, val) in vars(args).items() if val is not None and not (isinstance(val, Iterable) and not val)
    }
    assert 'foundry_root' in stripped_args
    assert str(stripped_args['foundry_root']) == str(TEST_TOML.parents[0])


def test_toml_specific_options() -> None:
    parser = _create_argument_parser()
    cmd_args = ['build', '--config-file', str(TEST_TOML), '--config-profile', 'a_profile']
    args = parser.parse_args(cmd_args)
    args_dict = parse_toml_args(args, get_option_string_destination, get_argument_type_setter)
    assert 'o3' in args_dict
    assert args_dict['o3']
    assert 'requires' in args_dict
    assert args_dict['requires'] == ['xor-lemmas.k']
    assert 'imports' in args_dict
    assert args_dict['imports'] == ['TestBase:XOR-LEMMAS']


def test_toml_profiles() -> None:
    parser = _create_argument_parser()
    cmd_args = ['prove', '--config-file', str(TEST_TOML), '--config-profile', 'b_profile']
    args = parser.parse_args(cmd_args)
    args_dict = parse_toml_args(args)
    assert 'verbose' in args_dict
    assert args_dict['verbose']
    assert 'debug' in args_dict
    assert args_dict['debug']
    assert 'workers' in args_dict
    assert args_dict['workers'] == 5
    assert 'smt_timeout' in args_dict
    assert args_dict['smt_timeout'] == 1000


def test_rpc_commands_fall_back_to_prove_profile(tmp_path: Path) -> None:
    parser = _create_argument_parser()
    toml_path = tmp_path / 'kontrol.toml'
    toml_path.write_text(
        '\n'.join(
            [
                '[prove.default]',
                "foundry-project-root = '.'",
                'workers = 4',
                'smt-timeout = 1000',
                'reinit = false',
            ]
        )
    )

    def _args_dict(*cmd_args: str) -> dict:
        args = parser.parse_args(list(cmd_args))
        return _parse_toml_args(args)

    simplify_node_args = _args_dict('simplify-node', '--config-file', str(toml_path), 'some_test', '1')
    assert simplify_node_args['workers'] == 4
    assert simplify_node_args['smt_timeout'] == 1000
    assert simplify_node_args['reinit'] is False

    step_node_args = _args_dict('step-node', '--config-file', str(toml_path), 'some_test', '1')
    assert step_node_args['workers'] == 4
    assert step_node_args['smt_timeout'] == 1000

    section_edge_args = _args_dict('section-edge', '--config-file', str(toml_path), 'some_test', '1,2')
    assert section_edge_args['workers'] == 4
    assert section_edge_args['smt_timeout'] == 1000

    get_model_args = _args_dict('get-model', '--config-file', str(toml_path), 'some_test')
    assert get_model_args['workers'] == 4
    assert get_model_args['smt_timeout'] == 1000


def test_command_profile_overrides_prove_fallback(tmp_path: Path) -> None:
    parser = _create_argument_parser()
    toml_path = tmp_path / 'kontrol.toml'
    toml_path.write_text(
        '\n'.join(
            [
                '[prove.default]',
                "foundry-project-root = '.'",
                'workers = 4',
                'smt-timeout = 1000',
                'reinit = false',
                '',
                '[simplify-node.default]',
                'smt-timeout = 250',
                'reinit = true',
            ]
        )
    )

    args = parser.parse_args(['simplify-node', '--config-file', str(toml_path), 'some_test', '1'])
    args_dict = _parse_toml_args(args)

    assert args_dict['workers'] == 4
    assert args_dict['smt_timeout'] == 250
    assert args_dict['reinit'] is True


def _prove_options(cmd_args: list[str]) -> ProveOptions:
    parser = _create_argument_parser()
    args = parser.parse_args(['prove', *cmd_args])
    stripped_args = {
        key: val for (key, val) in vars(args).items() if val is not None and not (isinstance(val, Iterable) and not val)
    }
    options = generate_options(stripped_args)
    assert isinstance(options, ProveOptions)
    return options


def test_haskell_logging_options() -> None:
    options = _prove_options(
        [
            '--haskell-log-dir',
            '/tmp/hlog',
            '--haskell-log-entries',
            'Abort,Simplify,Rewrite',
            '--booster-only-simplify',
        ]
    )
    assert options.haskell_log_dir == Path('/tmp/hlog')
    assert options.haskell_log_entries == ['Abort', 'Simplify', 'Rewrite']
    assert options.booster_only_simplify is True


def test_haskell_logging_option_defaults() -> None:
    options = _prove_options([])
    assert options.haskell_log_dir is None
    assert options.haskell_log_entries == list(HASKELL_LOGGING_ENTRIES)
    assert options.booster_only_simplify is False
