from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pyk
from pyk.kbuild.utils import KVersion, k_version

if TYPE_CHECKING:
    from typing import Final
    from pyk.cterm import CTerm
    from argparse import Namespace

import os
import stat

from rich.console import Console

from . import VERSION

console = Console()

_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'
_LOGGER: Final = logging.getLogger(__name__)


def ensure_name_is_unique(name: str, cterm: CTerm) -> str:
    """Ensure that a given name for a KVariable is unique within the context of a CTerm.

    :param name: name of a KVariable
    :param cterm: cterm
    :return: Returns the name if it's not used, otherwise appends a suffix.
    :rtype: str
    """
    if name not in cterm.free_vars:
        return name

    index = next(i for i in range(len(cterm.free_vars) + 1) if f'{name}_{i}' not in cterm.free_vars)
    return f'{name}_{index}'


def check_k_version() -> None:
    expected_k_version = KVersion.parse(f'v{pyk.__version__}')
    actual_k_version = k_version()

    if not _compare_versions(expected_k_version, actual_k_version):
        _LOGGER.warning(
            f'K version {expected_k_version.text} was expected but K version {actual_k_version.text} is being used.'
        )


def _compare_versions(ver1: KVersion, ver2: KVersion) -> bool:
    if ver1.major != ver2.major or ver1.minor != ver2.minor or ver1.patch != ver2.patch:
        return False

    if ver1.git == ver2.git:
        return True

    if ver1.git and ver2.git:
        return False

    git = ver1.git or ver2.git
    assert git  # git is not None for exactly one of ver1 and ver2
    return not git.ahead and not git.dirty


def config_file_path(args: Namespace) -> Path:
    return (
        Path.joinpath(
            Path('.') if not getattr(args, 'foundry_root', None) else args.foundry_root,
            'kontrol.toml',
        )
        if not getattr(args, 'config_file', None)
        else args.config_file
    )


def loglevel(args: Namespace, toml_args: dict) -> int:
    def is_attr_used(attr_name: str) -> bool | None:
        return getattr(args, attr_name, None) or toml_args.get(attr_name)

    if is_attr_used('debug'):
        return logging.DEBUG

    if is_attr_used('verbose'):
        return logging.INFO

    return logging.WARNING


def _read_digest_file(digest_file: Path) -> dict:
    if digest_file.exists():
        digest_dict = json.loads(digest_file.read_text())
    else:
        digest_dict = {}
    if 'methods' not in digest_dict:
        digest_dict['methods'] = {}
    return digest_dict


def kontrol_up_to_date(digest_file: Path) -> bool:
    if not digest_file.exists():
        return False
    digest_dict = _read_digest_file(digest_file)
    return digest_dict.get('kontrol', '') == VERSION


def parse_test_version_tuple(value: str) -> tuple[str, int | None]:
    if ':' in value:
        test, version = value.split(':')
        return (test, int(version))
    else:
        return (value, None)


def write_to_file(file_path: Path, content: str, grant_exec_permission: bool = False) -> None:
    """
    Writes the given content to a file specified by the file path with or without execution rights.

    Args:
    - file_path: Path object representing the path to the file including the file name.
    - content: A string containing the content to be written to the file.
    """
    try:
        with file_path.open('w', encoding='utf-8') as file:
            file.write(content)
            if grant_exec_permission:
                # Grant execute permission
                # Fetch current permissions
                current_permissions = os.stat(file_path).st_mode
                # Add execute permissions
                os.chmod(file_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception as e:
        print(f'An error occurred while writing to the file: {e}')


def append_to_file(file_path: Path, content: str) -> None:
    """Appends the given content to a file specified by the file path."""
    try:
        with file_path.open('a', encoding='utf-8') as file:
            file.write(content)
    except Exception as e:
        print(f'An error occurred while writing to the file: {e}')


def empty_lemmas_file_contents() -> str:
    return """module KONTROL-LEMMAS

    imports FOUNDRY-MAIN

// Your lemmas go here
// Not sure what to do next? Try checking the documentation for writing lemmas: https://docs.runtimeverification.com/kontrol/guides/advancing-proofs/kevm-lemmas

endmodule
"""


def kontrol_file_contents() -> str:
    return """
## Kontrol

**Kontrol grants developers the ability to perform formal verification without learning a new language or tool.**

## Documentation

https://docs.runtimeverification.com/kontrol/cheatsheets/kontrol-cheatsheet

## Usage

### Build

```shell
$ kontrol build
```

### Test

```shell
$ kontrol prove --match-test 'ContractName.TestName()'
```

### List

```shell
$ kontrol list
```

### Show

```shell
$ kontrol show --match-test 'ContractName.TestName()'
```

### Explore KCFG

```shell
$ kontrol view-kcfg 'ContractName.TestName()'
```

### Clean

```shell
$ kontrol clean
```


### Help

```shell
$ kontrol --help
$ kontrol command --help
```
"""


def kontrol_toml_file_contents() -> str:
    return """[build.default]
foundry-project-root       = '.'
regen                      = false
rekompile                  = false
verbose                    = false
debug                      = false
require                    = 'lemmas.k'
module-import              = 'TestBase:KONTROL-LEMMAS'
auxiliary-lemmas           = true
o2                         = true

[prove.default]
foundry-project-root       = '.'
verbose                    = false
debug                      = false
max-depth                  = 25000
reinit                     = false
cse                        = false
workers                    = 4
failure-information        = true
counterexample-information = true
minimize-proofs            = false
fail-fast                  = true
smt-timeout                = 1000
break-every-step           = false
break-on-jumpi             = false
break-on-calls             = false
break-on-storage           = false
break-on-basic-blocks      = false
break-on-cheatcodes        = false
run-constructor            = false
no-stack-checks            = true

[show.default]
foundry-project-root       = '.'
verbose                    = false
debug                      = false
use-hex-encoding           = false

[view-kcfg.default]
foundry-project-root       = '.'
use-hex-encoding           = false
"""


def foundry_toml_cancun_schedule() -> str:
    return """
evm_version = "cancun"
"""


def _rv_yellow() -> str:
    return '#ffcc07'


def _rv_blue() -> str:
    return '#0097cb'
