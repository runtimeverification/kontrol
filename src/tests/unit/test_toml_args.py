from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from pyk.cli.pyk import parse_toml_args

from kontrol.cli import _create_argument_parser, get_argument_type_setter, get_option_string_destination

from .utils import TEST_DATA_DIR

if TYPE_CHECKING:
    from typing import Final


TEST_TOML: Final = TEST_DATA_DIR / 'kontrol_test.toml'


def test_optionless_command() -> None:
    parser = _create_argument_parser()
    args = parser.parse_args(['version'])
    assert hasattr(args, 'config_file') == False
    assert args.command == 'version'


def test_continue_when_default_toml_absent() -> None:
    parser = _create_argument_parser()
    cmd_args = ['build', '--foundry-project-root', '.']
    args = parser.parse_args(cmd_args)
    assert hasattr(args, 'config_file')
    assert str(args.config_file) == 'kontrol.toml'
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
