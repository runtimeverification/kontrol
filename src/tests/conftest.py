from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pyk.cli.utils import dir_path

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import FixtureRequest, Parser


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        '--foundry-root',
        type=dir_path,
        help='Use pre-kompiled project directory for proof tests',
    )
    parser.addoption(
        '--update-expected-output',
        action='store_true',
        default=False,
        help='Write expected output files for proof tests',
    )
    parser.addoption(
        '--force-sequential',
        default=False,
        action='store_true',
        help='Use sequential, single-threaded proof loop.',
    )


@pytest.fixture(scope='session')
def foundry_root_dir(request: FixtureRequest) -> Path | None:
    return request.config.getoption('--foundry-root')


@pytest.fixture
def update_expected_output(request: FixtureRequest) -> bool:
    return request.config.getoption('--update-expected-output')


@pytest.fixture(scope='session')
def force_sequential(request: FixtureRequest) -> bool:
    return request.config.getoption('--force-sequential')
