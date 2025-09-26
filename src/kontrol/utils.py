from __future__ import annotations

import ast
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pyk
from eth_abi import decode
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


def read_contract_names(contract_names: Path) -> dict[str, str]:
    if not contract_names.exists():
        raise FileNotFoundError(f'Contract names dictionary file not found: {contract_names}')
    return json.loads(contract_names.read_text())


def parse_test_version_tuple(value: str) -> tuple[str, int | None]:
    if ':' in value:
        test, version = value.split(':')
        return (test, int(version))
    else:
        return (value, None)


def hex_string_to_int(hex: str) -> int:
    if hex.startswith('0x'):
        return int(hex, 16)
    else:
        raise ValueError('Invalid hex format')


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
    return """requires "kontrol.md"

module KONTROL-LEMMAS
    imports KONTROL-BASE

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
run-constructor            = true
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


def foundry_toml_use_optimizer() -> str:
    return """
optimizer = true
"""


def _rv_yellow() -> str:
    return '#ffcc07'


def _rv_blue() -> str:
    return '#0097cb'


def replace_k_words(text: str) -> str:
    replacements = {
        '+Int': '+',
        '-Int': '-',
        '*Int': '*',
        '/Int': '/',
        'divInt': '/',
        'modInt': '%',
        'orBool': '||',
        'andBool': '&&',
        'notBool': '!',
        '#Equals': '==',
        'NUMBER_CELL': 'block.number',
        'TIMESTAMP_CELL': 'block.timestamp',
        ':Int': '',
        ':Bytes': '',
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r'\bKV\d*_', '', text)

    return text


def decode_log_message(token: str, selector: int) -> str | None:
    if selector == EMPTY_LOG_SELECTOR:
        return ''
    elif selector in CONSOLE_SELECTORS:
        param_types = CONSOLE_SELECTORS[selector]
        decoded = decode(param_types, ast.literal_eval(token))
        output = ' '.join(str(item) for item in decoded)
        return output
    else:
        _LOGGER.warning(f'Unknown console logging function: 0x{selector:08x}')
        return None


EMPTY_LOG_SELECTOR = 1368866505
# a mapping from function selectors to the argument types used in the log functions from
# https://github.com/foundry-rs/forge-std/blob/ee93fdc45d1e5e4dee883afe0103109881a83549/src/console.sol
CONSOLE_SELECTORS: Final[dict[int, list[str]]] = {
    1696970229: ['int256'],
    2567288644: ['uint256'],
    196436950: ['string'],
    3128604750: ['bool'],
    1603383471: ['address'],
    3782998358: ['bytes'],
    1866559945: ['bytes1'],
    2606666814: ['bytes2'],
    2005072429: ['bytes3'],
    4221807929: ['bytes4'],
    1434697262: ['bytes5'],
    1229106630: ['bytes6'],
    1165275051: ['bytes7'],
    2567103615: ['bytes8'],
    1352743135: ['bytes9'],
    2646780055: ['bytes10'],
    3691558567: ['bytes11'],
    1985402567: ['bytes12'],
    885119003: ['bytes13'],
    1022016101: ['bytes14'],
    1494891938: ['bytes15'],
    529363730: ['bytes16'],
    4170863407: ['bytes17'],
    3630507586: ['bytes18'],
    16083913: ['bytes19'],
    3971503742: ['bytes20'],
    810729615: ['bytes21'],
    2155525172: ['bytes22'],
    1232711735: ['bytes23'],
    158838524: ['bytes24'],
    2930349631: ['bytes25'],
    3546502696: ['bytes26'],
    4231475103: ['bytes27'],
    942643764: ['bytes28'],
    2048423489: ['bytes29'],
    3291746038: ['bytes30'],
    2180810312: ['bytes31'],
    757192439: ['bytes32'],
    4163653873: ['uint256'],
    760966329: ['int256'],
    1093685164: ['string'],
    843419373: ['bool'],
    741264322: ['address'],
    4133908826: ['uint256', 'uint256'],
    1681903839: ['uint256', 'string'],
    480083635: ['uint256', 'bool'],
    1764191366: ['uint256', 'address'],
    3054400204: ['string', 'uint256'],
    1017521806: ['string', 'int256'],
    1264337527: ['string', 'string'],
    3283441205: ['string', 'bool'],
    832238387: ['string', 'address'],
    965833939: ['bool', 'uint256'],
    2414527781: ['bool', 'string'],
    705760899: ['bool', 'bool'],
    2235320393: ['bool', 'address'],
    2198464680: ['address', 'uint256'],
    1973388987: ['address', 'string'],
    1974863315: ['address', 'bool'],
    3673216170: ['address', 'address'],
    3522001468: ['uint256', 'uint256', 'uint256'],
    1909476082: ['uint256', 'uint256', 'string'],
    1197922930: ['uint256', 'uint256', 'bool'],
    1553380145: ['uint256', 'uint256', 'address'],
    933920076: ['uint256', 'string', 'uint256'],
    2970968351: ['uint256', 'string', 'string'],
    1290643290: ['uint256', 'string', 'bool'],
    2063255897: ['uint256', 'string', 'address'],
    537493524: ['uint256', 'bool', 'uint256'],
    2239189025: ['uint256', 'bool', 'string'],
    544310864: ['uint256', 'bool', 'bool'],
    889741179: ['uint256', 'bool', 'address'],
    1520131797: ['uint256', 'address', 'uint256'],
    1674265081: ['uint256', 'address', 'string'],
    2607726658: ['uint256', 'address', 'bool'],
    3170737120: ['uint256', 'address', 'address'],
    3393701099: ['string', 'uint256', 'uint256'],
    1500569737: ['string', 'uint256', 'string'],
    3396809649: ['string', 'uint256', 'bool'],
    478069832: ['string', 'uint256', 'address'],
    1478619041: ['string', 'string', 'uint256'],
    753761519: ['string', 'string', 'string'],
    2967534005: ['string', 'string', 'bool'],
    2515337621: ['string', 'string', 'address'],
    3378075862: ['string', 'bool', 'uint256'],
    3801674877: ['string', 'bool', 'string'],
    2232122070: ['string', 'bool', 'bool'],
    2469116728: ['string', 'bool', 'address'],
    220641573: ['string', 'address', 'uint256'],
    3773410639: ['string', 'address', 'string'],
    3374145236: ['string', 'address', 'bool'],
    4243355104: ['string', 'address', 'address'],
    923808615: ['bool', 'uint256', 'uint256'],
    3288086896: ['bool', 'uint256', 'string'],
    3906927529: ['bool', 'uint256', 'bool'],
    143587794: ['bool', 'uint256', 'address'],
    278130193: ['bool', 'string', 'uint256'],
    2960557183: ['bool', 'string', 'string'],
    3686056519: ['bool', 'string', 'bool'],
    2509355347: ['bool', 'string', 'address'],
    317855234: ['bool', 'bool', 'uint256'],
    626391622: ['bool', 'bool', 'string'],
    1349555864: ['bool', 'bool', 'bool'],
    276362893: ['bool', 'bool', 'address'],
    1601936123: ['bool', 'address', 'uint256'],
    3734671984: ['bool', 'address', 'string'],
    415876934: ['bool', 'address', 'bool'],
    3530962535: ['bool', 'address', 'address'],
    3063663350: ['address', 'uint256', 'uint256'],
    2717051050: ['address', 'uint256', 'string'],
    1736575400: ['address', 'uint256', 'bool'],
    2076235848: ['address', 'uint256', 'address'],
    1742565361: ['address', 'string', 'uint256'],
    4218888805: ['address', 'string', 'string'],
    3473018801: ['address', 'string', 'bool'],
    4035396840: ['address', 'string', 'address'],
    2622462459: ['address', 'bool', 'uint256'],
    555898316: ['address', 'bool', 'string'],
    3951234194: ['address', 'bool', 'bool'],
    4044790253: ['address', 'bool', 'address'],
    402547077: ['address', 'address', 'uint256'],
    7426238: ['address', 'address', 'string'],
    4070990470: ['address', 'address', 'bool'],
    25986242: ['address', 'address', 'address'],
    423606272: ['uint256', 'uint256', 'uint256', 'uint256'],
    1506790371: ['uint256', 'uint256', 'uint256', 'string'],
    3315126661: ['uint256', 'uint256', 'uint256', 'bool'],
    4202792367: ['uint256', 'uint256', 'uint256', 'address'],
    1570936811: ['uint256', 'uint256', 'string', 'uint256'],
    668512210: ['uint256', 'uint256', 'string', 'string'],
    2062986021: ['uint256', 'uint256', 'string', 'bool'],
    1121066423: ['uint256', 'uint256', 'string', 'address'],
    3950997458: ['uint256', 'uint256', 'bool', 'uint256'],
    2780101785: ['uint256', 'uint256', 'bool', 'string'],
    2869451494: ['uint256', 'uint256', 'bool', 'bool'],
    2592172675: ['uint256', 'uint256', 'bool', 'address'],
    2297881778: ['uint256', 'uint256', 'address', 'uint256'],
    1826504888: ['uint256', 'uint256', 'address', 'string'],
    365610102: ['uint256', 'uint256', 'address', 'bool'],
    1453707697: ['uint256', 'uint256', 'address', 'address'],
    2193775476: ['uint256', 'string', 'uint256', 'uint256'],
    3082360010: ['uint256', 'string', 'uint256', 'string'],
    1763348340: ['uint256', 'string', 'uint256', 'bool'],
    992115124: ['uint256', 'string', 'uint256', 'address'],
    2955463101: ['uint256', 'string', 'string', 'uint256'],
    564987523: ['uint256', 'string', 'string', 'string'],
    3014047421: ['uint256', 'string', 'string', 'bool'],
    3582182914: ['uint256', 'string', 'string', 'address'],
    3472922752: ['uint256', 'string', 'bool', 'uint256'],
    3537118157: ['uint256', 'string', 'bool', 'string'],
    3126025628: ['uint256', 'string', 'bool', 'bool'],
    2922300801: ['uint256', 'string', 'bool', 'address'],
    3906142605: ['uint256', 'string', 'address', 'uint256'],
    2621104033: ['uint256', 'string', 'address', 'string'],
    2428701270: ['uint256', 'string', 'address', 'bool'],
    1634266465: ['uint256', 'string', 'address', 'address'],
    3333212072: ['uint256', 'bool', 'uint256', 'uint256'],
    3724797812: ['uint256', 'bool', 'uint256', 'string'],
    2443193898: ['uint256', 'bool', 'uint256', 'bool'],
    2295029825: ['uint256', 'bool', 'uint256', 'address'],
    740099910: ['uint256', 'bool', 'string', 'uint256'],
    1757984957: ['uint256', 'bool', 'string', 'string'],
    3952250239: ['uint256', 'bool', 'string', 'bool'],
    4015165464: ['uint256', 'bool', 'string', 'address'],
    1952763427: ['uint256', 'bool', 'bool', 'uint256'],
    3722155361: ['uint256', 'bool', 'bool', 'string'],
    3069540257: ['uint256', 'bool', 'bool', 'bool'],
    1768164185: ['uint256', 'bool', 'bool', 'address'],
    125994997: ['uint256', 'bool', 'address', 'uint256'],
    2917159623: ['uint256', 'bool', 'address', 'string'],
    1162695845: ['uint256', 'bool', 'address', 'bool'],
    2716814523: ['uint256', 'bool', 'address', 'address'],
    211605953: ['uint256', 'address', 'uint256', 'uint256'],
    3719324961: ['uint256', 'address', 'uint256', 'string'],
    1601452668: ['uint256', 'address', 'uint256', 'bool'],
    364980149: ['uint256', 'address', 'uint256', 'address'],
    1182952285: ['uint256', 'address', 'string', 'uint256'],
    1041403043: ['uint256', 'address', 'string', 'string'],
    3425872647: ['uint256', 'address', 'string', 'bool'],
    2629472255: ['uint256', 'address', 'string', 'address'],
    1522374954: ['uint256', 'address', 'bool', 'uint256'],
    2432370346: ['uint256', 'address', 'bool', 'string'],
    3813741583: ['uint256', 'address', 'bool', 'bool'],
    4017276179: ['uint256', 'address', 'bool', 'address'],
    1936653238: ['uint256', 'address', 'address', 'uint256'],
    52195187: ['uint256', 'address', 'address', 'string'],
    153090805: ['uint256', 'address', 'address', 'bool'],
    612938772: ['uint256', 'address', 'address', 'address'],
    2812835923: ['string', 'uint256', 'uint256', 'uint256'],
    2236298390: ['string', 'uint256', 'uint256', 'string'],
    1982258066: ['string', 'uint256', 'uint256', 'bool'],
    3793609336: ['string', 'uint256', 'uint256', 'address'],
    3330189777: ['string', 'uint256', 'string', 'uint256'],
    1522028063: ['string', 'uint256', 'string', 'string'],
    2099530013: ['string', 'uint256', 'string', 'bool'],
    2084975268: ['string', 'uint256', 'string', 'address'],
    3827003247: ['string', 'uint256', 'bool', 'uint256'],
    2885106328: ['string', 'uint256', 'bool', 'string'],
    894187222: ['string', 'uint256', 'bool', 'bool'],
    3773389720: ['string', 'uint256', 'bool', 'address'],
    1325727174: ['string', 'uint256', 'address', 'uint256'],
    2684039059: ['string', 'uint256', 'address', 'string'],
    2182163010: ['string', 'uint256', 'address', 'bool'],
    1587722158: ['string', 'uint256', 'address', 'address'],
    4099767596: ['string', 'string', 'uint256', 'uint256'],
    1562023706: ['string', 'string', 'uint256', 'string'],
    3282609748: ['string', 'string', 'uint256', 'bool'],
    270792626: ['string', 'string', 'uint256', 'address'],
    2393878571: ['string', 'string', 'string', 'uint256'],
    3731419658: ['string', 'string', 'string', 'string'],
    739726573: ['string', 'string', 'string', 'bool'],
    1834430276: ['string', 'string', 'string', 'address'],
    3601791698: ['string', 'string', 'bool', 'uint256'],
    1585754346: ['string', 'string', 'bool', 'string'],
    1081628777: ['string', 'string', 'bool', 'bool'],
    3279013851: ['string', 'string', 'bool', 'address'],
    2093204999: ['string', 'string', 'address', 'uint256'],
    3944480640: ['string', 'string', 'address', 'string'],
    1556958775: ['string', 'string', 'address', 'bool'],
    1134328815: ['string', 'string', 'address', 'address'],
    1689631591: ['string', 'bool', 'uint256', 'uint256'],
    1949134567: ['string', 'bool', 'uint256', 'string'],
    2331496330: ['string', 'bool', 'uint256', 'bool'],
    2472413631: ['string', 'bool', 'uint256', 'address'],
    620303461: ['string', 'bool', 'string', 'uint256'],
    2821114603: ['string', 'bool', 'string', 'string'],
    1066037277: ['string', 'bool', 'string', 'bool'],
    3764542249: ['string', 'bool', 'string', 'address'],
    2386524329: ['string', 'bool', 'bool', 'uint256'],
    2636305885: ['string', 'bool', 'bool', 'string'],
    2304440517: ['string', 'bool', 'bool', 'bool'],
    1905304873: ['string', 'bool', 'bool', 'address'],
    1560853253: ['string', 'bool', 'address', 'uint256'],
    764294052: ['string', 'bool', 'address', 'string'],
    2508990662: ['string', 'bool', 'address', 'bool'],
    870964509: ['string', 'bool', 'address', 'address'],
    4176812830: ['string', 'address', 'uint256', 'uint256'],
    1514632754: ['string', 'address', 'uint256', 'string'],
    4232594928: ['string', 'address', 'uint256', 'bool'],
    1677429701: ['string', 'address', 'uint256', 'address'],
    2446397742: ['string', 'address', 'string', 'uint256'],
    609847026: ['string', 'address', 'string', 'string'],
    1595265676: ['string', 'address', 'string', 'bool'],
    2864486961: ['string', 'address', 'string', 'address'],
    1050642026: ['string', 'address', 'bool', 'uint256'],
    72663161: ['string', 'address', 'bool', 'string'],
    2038975531: ['string', 'address', 'bool', 'bool'],
    573965245: ['string', 'address', 'bool', 'address'],
    2398352281: ['string', 'address', 'address', 'uint256'],
    2148146279: ['string', 'address', 'address', 'string'],
    3047013728: ['string', 'address', 'address', 'bool'],
    3985582326: ['string', 'address', 'address', 'address'],
    927708338: ['bool', 'uint256', 'uint256', 'uint256'],
    2389310301: ['bool', 'uint256', 'uint256', 'string'],
    3197649747: ['bool', 'uint256', 'uint256', 'bool'],
    14518201: ['bool', 'uint256', 'uint256', 'address'],
    1779538402: ['bool', 'uint256', 'string', 'uint256'],
    4122747465: ['bool', 'uint256', 'string', 'string'],
    3857124139: ['bool', 'uint256', 'string', 'bool'],
    4275904511: ['bool', 'uint256', 'string', 'address'],
    2140912802: ['bool', 'uint256', 'bool', 'uint256'],
    2437143473: ['bool', 'uint256', 'bool', 'string'],
    3468031191: ['bool', 'uint256', 'bool', 'bool'],
    2597139990: ['bool', 'uint256', 'bool', 'address'],
    355982471: ['bool', 'uint256', 'address', 'uint256'],
    464760986: ['bool', 'uint256', 'address', 'string'],
    3032683775: ['bool', 'uint256', 'address', 'bool'],
    653615272: ['bool', 'uint256', 'address', 'address'],
    679886795: ['bool', 'string', 'uint256', 'uint256'],
    450457062: ['bool', 'string', 'uint256', 'string'],
    1796103507: ['bool', 'string', 'uint256', 'bool'],
    362193358: ['bool', 'string', 'uint256', 'address'],
    2078327787: ['bool', 'string', 'string', 'uint256'],
    392356650: ['bool', 'string', 'string', 'string'],
    508266469: ['bool', 'string', 'string', 'bool'],
    2547225816: ['bool', 'string', 'string', 'address'],
    369533843: ['bool', 'string', 'bool', 'uint256'],
    1211958294: ['bool', 'string', 'bool', 'string'],
    3697185627: ['bool', 'string', 'bool', 'bool'],
    1401816747: ['bool', 'string', 'bool', 'address'],
    2781534868: ['bool', 'string', 'address', 'uint256'],
    316065672: ['bool', 'string', 'address', 'string'],
    1842623690: ['bool', 'string', 'address', 'bool'],
    724244700: ['bool', 'string', 'address', 'address'],
    196087467: ['bool', 'bool', 'uint256', 'uint256'],
    2111099104: ['bool', 'bool', 'uint256', 'string'],
    1637764366: ['bool', 'bool', 'uint256', 'bool'],
    1420274080: ['bool', 'bool', 'uint256', 'address'],
    3819555375: ['bool', 'bool', 'string', 'uint256'],
    1830717265: ['bool', 'bool', 'string', 'string'],
    3092715066: ['bool', 'bool', 'string', 'bool'],
    4188875657: ['bool', 'bool', 'string', 'address'],
    1836074433: ['bool', 'bool', 'bool', 'uint256'],
    719587540: ['bool', 'bool', 'bool', 'string'],
    992632032: ['bool', 'bool', 'bool', 'bool'],
    2352126746: ['bool', 'bool', 'bool', 'address'],
    1276263767: ['bool', 'bool', 'address', 'uint256'],
    2695133539: ['bool', 'bool', 'address', 'string'],
    3231908568: ['bool', 'bool', 'address', 'bool'],
    4102557348: ['bool', 'bool', 'address', 'address'],
    2079424929: ['bool', 'address', 'uint256', 'uint256'],
    1374724088: ['bool', 'address', 'uint256', 'string'],
    3590430492: ['bool', 'address', 'uint256', 'bool'],
    325780957: ['bool', 'address', 'uint256', 'address'],
    3256837319: ['bool', 'address', 'string', 'uint256'],
    2805734838: ['bool', 'address', 'string', 'string'],
    3804222987: ['bool', 'address', 'string', 'bool'],
    1870422078: ['bool', 'address', 'string', 'address'],
    126031106: ['bool', 'address', 'bool', 'uint256'],
    1248250676: ['bool', 'address', 'bool', 'string'],
    1788626827: ['bool', 'address', 'bool', 'bool'],
    474063670: ['bool', 'address', 'bool', 'address'],
    208064958: ['bool', 'address', 'address', 'uint256'],
    3625099623: ['bool', 'address', 'address', 'string'],
    1180699616: ['bool', 'address', 'address', 'bool'],
    487903233: ['bool', 'address', 'address', 'address'],
    888202806: ['address', 'uint256', 'uint256', 'uint256'],
    1244184599: ['address', 'uint256', 'uint256', 'string'],
    1727118439: ['address', 'uint256', 'uint256', 'bool'],
    551786573: ['address', 'uint256', 'uint256', 'address'],
    3204577425: ['address', 'uint256', 'string', 'uint256'],
    2292761606: ['address', 'uint256', 'string', 'string'],
    3474460764: ['address', 'uint256', 'string', 'bool'],
    1547898183: ['address', 'uint256', 'string', 'address'],
    586594713: ['address', 'uint256', 'bool', 'uint256'],
    3316483577: ['address', 'uint256', 'bool', 'string'],
    1005970743: ['address', 'uint256', 'bool', 'bool'],
    2736520652: ['address', 'uint256', 'bool', 'address'],
    269444366: ['address', 'uint256', 'address', 'uint256'],
    497649386: ['address', 'uint256', 'address', 'string'],
    2713504179: ['address', 'uint256', 'address', 'bool'],
    1200430178: ['address', 'uint256', 'address', 'address'],
    499704248: ['address', 'string', 'uint256', 'uint256'],
    1149776040: ['address', 'string', 'uint256', 'string'],
    251125840: ['address', 'string', 'uint256', 'bool'],
    1662531192: ['address', 'string', 'uint256', 'address'],
    362776871: ['address', 'string', 'string', 'uint256'],
    1560462603: ['address', 'string', 'string', 'string'],
    900007711: ['address', 'string', 'string', 'bool'],
    2689478535: ['address', 'string', 'string', 'address'],
    1365129398: ['address', 'string', 'bool', 'uint256'],
    3154862590: ['address', 'string', 'bool', 'string'],
    1595759775: ['address', 'string', 'bool', 'bool'],
    542667202: ['address', 'string', 'bool', 'address'],
    1166009295: ['address', 'string', 'address', 'uint256'],
    4158874181: ['address', 'string', 'address', 'string'],
    233909110: ['address', 'string', 'address', 'bool'],
    221706784: ['address', 'string', 'address', 'address'],
    946861556: ['address', 'bool', 'uint256', 'uint256'],
    178704301: ['address', 'bool', 'uint256', 'string'],
    3294903840: ['address', 'bool', 'uint256', 'bool'],
    3438776481: ['address', 'bool', 'uint256', 'address'],
    2162598411: ['address', 'bool', 'string', 'uint256'],
    1197235251: ['address', 'bool', 'string', 'string'],
    1353532957: ['address', 'bool', 'string', 'bool'],
    436029782: ['address', 'bool', 'string', 'address'],
    2353946086: ['address', 'bool', 'bool', 'uint256'],
    3754205928: ['address', 'bool', 'bool', 'string'],
    3401856121: ['address', 'bool', 'bool', 'bool'],
    3476636805: ['address', 'bool', 'bool', 'address'],
    2807847390: ['address', 'bool', 'address', 'uint256'],
    769095910: ['address', 'bool', 'address', 'string'],
    2801077007: ['address', 'bool', 'address', 'bool'],
    1711502813: ['address', 'bool', 'address', 'address'],
    3193255041: ['address', 'address', 'uint256', 'uint256'],
    4256496016: ['address', 'address', 'uint256', 'string'],
    2604815586: ['address', 'address', 'uint256', 'bool'],
    2376523509: ['address', 'address', 'uint256', 'address'],
    4011651047: ['address', 'address', 'string', 'uint256'],
    566079269: ['address', 'address', 'string', 'string'],
    1863997774: ['address', 'address', 'string', 'bool'],
    2406706454: ['address', 'address', 'string', 'address'],
    963766156: ['address', 'address', 'bool', 'uint256'],
    2858762440: ['address', 'address', 'bool', 'string'],
    752096074: ['address', 'address', 'bool', 'bool'],
    2669396846: ['address', 'address', 'bool', 'address'],
    2485456247: ['address', 'address', 'address', 'uint256'],
    4161329696: ['address', 'address', 'address', 'string'],
    238520724: ['address', 'address', 'address', 'bool'],
    1717301556: ['address', 'address', 'address', 'address'],
}


def kontrol_test_file_contents() -> str:
    return """pragma solidity ^0.8.26;
import "forge-std/Vm.sol";
import "forge-std/Test.sol";
import "kontrol-cheatcodes/KontrolCheats.sol";

contract KontrolTest is Test, KontrolCheats {
    enum Mode {
        Assume,
        Try,
        Assert
    }
    function _establish(Mode mode, bool condition) internal pure returns (bool) {
        if (mode == Mode.Assume) {
            vm.assume(condition);
            return true;
        } else if (mode == Mode.Try) {
            return condition;
        } else {
            assert(condition);
            return true;
        }
    }
    function _loadData(
        address contractAddress,
        uint256 slot,
        uint256 offset,
        uint256 width
    ) internal view returns (uint256) {
        require(contractAddress != address(0), 'Invalid contract address');
        require(width > 0, 'Width must be greater than 0');
        // `offset` and `width` must not overflow the slot
        assert(offset + width <= 32);
        
        // Slot read mask - handle width = 32 case to prevent overflow
        uint256 mask;
        if (width == 32) {
            mask = type(uint256).max;
        } else {
            unchecked {
                mask = (2 ** (8 * width)) - 1;
            }
        }
        // Value right shift
        uint256 shift = 8 * offset;
        // Current slot value
        uint256 slotValue = uint256(vm.load(contractAddress, bytes32(slot)));
        // Isolate and return data to retrieve
        return mask & (slotValue >> shift);
    }
    function _storeData(address contractAddress, uint256 slot, uint256 offset, uint256 width, uint256 value) internal {
        // `offset` and `width` must not overflow the slot
        assert(offset + width <= 32);
        // and `value` must fit into the designated part
        assert(width == 32 || value < 2 ** (8 * width));
        // Slot update mask
        uint256 maskLeft;
        unchecked {
            maskLeft = ~((2 ** (8 * (offset + width))) - 1);
        }
        uint256 maskRight = (2 ** (8 * offset)) - 1;
        uint256 mask = maskLeft | maskRight;
        uint256 updatedValue = (2 ** (8 * offset)) * value;
        // Current slot value
        uint256 slotValue = uint256(vm.load(contractAddress, bytes32(slot)));
        // Updated slot value
        slotValue = updatedValue | (mask & slotValue);
        vm.store(contractAddress, bytes32(slot), bytes32(slotValue));
    }
    function _loadMappingData(
        address contractAddress,
        uint256 mappingSlot,
        uint256 key,
        uint256 subSlot,
        uint256 offset,
        uint256 width
    ) internal view returns (uint256) {
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        return _loadData(contractAddress, uint256(hashedSlot) + subSlot, offset, width);
    }
    function _storeMappingData(
        address contractAddress,
        uint256 mappingSlot,
        uint256 key,
        uint256 subSlot,
        uint256 offset,
        uint256 width,
        uint256 value
    ) internal {
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        _storeData(contractAddress, uint256(hashedSlot) + subSlot, offset, width, value);
    }
    function _loadUInt256(address contractAddress, uint256 slot) internal view returns (uint256) {
        return _loadData(contractAddress, slot, 0, 32);
    }
    function _loadMappingUInt256(
        address contractAddress,
        uint256 mappingSlot,
        uint256 key,
        uint256 subSlot
    ) internal view returns (uint256) {
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        return _loadData(contractAddress, uint256(hashedSlot) + subSlot, 0, 32);
    }
    function _loadAddress(address contractAddress, uint256 slot) internal view returns (address) {
        return address(uint160(_loadData(contractAddress, slot, 0, 20)));
    }
    function _storeMappingUInt256(
        address contractAddress,
        uint256 mappingSlot,
        uint256 key,
        uint256 subSlot,
        uint256 value
    ) internal {
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        _storeData(contractAddress, uint256(hashedSlot) + subSlot, 0, 32, value);
    }
    function _storeUInt256(address contractAddress, uint256 slot, uint256 value) internal {
        _storeData(contractAddress, slot, 0, 32, value);
    }
    function _storeAddress(address contractAddress, uint256 slot, address value) internal {
        _storeData(contractAddress, slot, 0, 20, uint160(value));
    }
    function _storeBytes32(address contractAddress, uint256 slot, bytes32 value) internal {
        _storeUInt256(contractAddress, slot, uint256(value));
    }
    function _assumeNoOverflow(uint256 augend, uint256 addend) internal pure {
        unchecked {
            vm.assume(augend < augend + addend);
        }
    }
    function _clearSlot(address contractAddress, uint256 slot) internal {
        _storeUInt256(contractAddress, slot, 0);
    }
    function _clearMappingSlot(address contractAddress, uint256 mappingSlot, uint256 key, uint256 subSlot) internal {
        bytes32 hashedSlot = keccak256(abi.encodePacked(key, mappingSlot));
        _storeData(contractAddress, uint256(hashedSlot) + subSlot, 0, 32, 0);
    }
}"""
