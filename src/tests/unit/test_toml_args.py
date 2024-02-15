from __future__ import annotations

from typing import TYPE_CHECKING

from kontrol.cli import _create_argument_parser, read_toml_args

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
    args = read_toml_args(parser, args, cmd_args[1:]) if hasattr(args, 'config_file') else args
    assert hasattr(args, 'config_file')
    assert str(args.config_file) == 'kontrol.toml'
    assert hasattr(args, 'config_profile')
    assert str(args.config_profile) == 'default'


def test_toml_read() -> None:
    parser = _create_argument_parser()
    cmd_args = ['build', '--config', str(TEST_TOML)]
    args = parser.parse_args(cmd_args)
    args = read_toml_args(parser, args, cmd_args[1:]) if hasattr(args, 'config_file') else args
    assert hasattr(args, 'verbose')
    assert not args.verbose
    assert hasattr(args, 'debug')
    assert not args.debug


def test_toml_read_default_profile() -> None:
    parser = _create_argument_parser()
    cmd_args = ['show', '--config', str(TEST_TOML), 'some_test']
    args = parser.parse_args(cmd_args)
    args = read_toml_args(parser, args, cmd_args[1:]) if hasattr(args, 'config_file') else args
    assert hasattr(args, 'verbose')
    assert args.verbose
    assert hasattr(args, 'debug')
    assert args.verbose
    assert hasattr(args, 'version')
    assert args.version == 3
    assert hasattr(args, 'node_deltas')
    assert len(args.node_deltas) == 1
    assert str(args.node_deltas) == "[(10, '#target')]"


def test_cli_overrides_toml() -> None:
    parser = _create_argument_parser()
    cmd_args = ['build', '--config', str(TEST_TOML), '--foundry-project-root', str(TEST_TOML.parents[0])]
    args = parser.parse_args(cmd_args)
    args = read_toml_args(parser, args, cmd_args[1:]) if hasattr(args, 'config_file') else args
    assert hasattr(args, 'foundry_root')
    assert str(args.foundry_root) == str(TEST_TOML.parents[0])


def test_toml_specific_options() -> None:
    parser = _create_argument_parser()
    cmd_args = ['build', '--config', str(TEST_TOML), '--config-profile', 'a_profile']
    args = parser.parse_args(cmd_args)
    args = read_toml_args(parser, args, cmd_args[1:]) if hasattr(args, 'config_file') else args
    assert hasattr(args, 'o3')
    assert args.o3


def test_toml_profiles() -> None:
    parser = _create_argument_parser()
    cmd_args = ['prove', '--config', str(TEST_TOML), '--config-profile', 'b_profile']
    args = parser.parse_args(cmd_args)
    args = read_toml_args(parser, args, cmd_args[1:]) if hasattr(args, 'config_file') else args
    assert hasattr(args, 'verbose')
    assert args.verbose
    assert hasattr(args, 'debug')
    assert args.verbose
    assert hasattr(args, 'workers')
    assert args.workers == 5
    assert hasattr(args, 'smt_timeout')
    assert args.smt_timeout == 1000
