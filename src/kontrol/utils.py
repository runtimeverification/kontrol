from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import os
import stat


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


def empty_lemmas_file_contents() -> str:
    return """
requires "evm.md"
requires "foundry.md"

module KONTROL-LEMMAS
    imports BOOL
    imports FOUNDRY
    imports INFINITE-GAS
    imports INT-SYMBOLIC

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
