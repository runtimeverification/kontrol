from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import os
import stat

from rich.console import Console

from . import VERSION

console = Console()


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
    return """requires "foundry.md"

module KONTROL-LEMMAS

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

[show.default]
foundry-project-root       = '.'
verbose                    = false
debug                      = false
use-hex-encoding           = false

[view-kcfg.default]
foundry-project-root       = '.'
use-hex-encoding           = false
"""


def foundry_toml_extra_contents() -> str:
    return """
extra_output = ['storageLayout']
"""


def _rv_yellow() -> str:
    return '#ffcc07'


def _rv_blue() -> str:
    return '#0097cb'
