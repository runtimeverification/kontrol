from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from eth_utils import to_checksum_address
from pyk.utils import ensure_dir_path

from .utils import hex_string_to_int, read_contract_names

if TYPE_CHECKING:
    from .options import LoadStateOptions


class SlotUpdate(NamedTuple):
    address: str
    slot: str
    value: str


class StorageUpdate(NamedTuple):
    slot: str
    value: str


@dataclass
class StateDiffEntry:
    kind: str
    account: str
    old_balance: int
    new_balance: int
    deployed_code: str
    reverted: bool
    storage_updates: tuple[SlotUpdate, ...]

    def __init__(self, e: dict) -> None:
        self.kind = e['kind']
        self.account = e['account']
        self.old_balance = e['oldBalance']
        self.new_balance = e['newBalance']
        self.deployed_code = e['deployedCode']
        self.reverted = e['reverted']
        self.storage_updates = self._get_storage_updates(e['storageAccesses'])

    @property
    def has_ignored_kind(self) -> bool:
        return self.kind in ['Balance', 'Extcodesize', 'Extcodehash', 'Extcodecopy']

    @property
    def is_create(self) -> bool:
        return self.deployed_code != '0x' and self.kind == 'Create'

    @property
    def updates_balance(self) -> bool:
        return self.new_balance != self.old_balance

    @staticmethod
    def _get_storage_updates(storage_access: list[dict]) -> tuple[SlotUpdate, ...]:
        storage_updates = []
        for _a in storage_access:
            account_storage = _a['account']
            slot = _a['slot']
            is_write = _a['isWrite']
            previous_value = _a['previousValue']
            new_value = _a['newValue']
            reverted = _a['reverted']

            if reverted or not is_write or new_value == previous_value:
                continue

            storage_updates.append(SlotUpdate(account_storage, slot, new_value))
        return tuple(storage_updates)


@dataclass
class StateDumpEntry:
    account: str
    balance: int
    code: str
    storage: tuple[StorageUpdate, ...]

    def __init__(self, acc: str, e: dict) -> None:
        self.account = to_checksum_address(acc)
        self.balance = hex_string_to_int(e['balance'])
        self.code = e['code']
        self.storage = self._get_storage_updates(e['storage'])

    @staticmethod
    def _get_storage_updates(storage_dump: dict) -> tuple[StorageUpdate, ...]:
        storage_updates = []
        for slot in storage_dump:
            storage_updates.append(StorageUpdate(slot, storage_dump[slot]))
        return tuple(storage_updates)


class RecreateState:
    SOLIDITY_VERSION = '^0.8.13'

    name: str
    commands: list[str]
    accounts: dict[str, str]  # address, name
    code: dict[str, str]

    def __init__(self, name: str, accounts: dict | None = None) -> None:
        self.commands = []
        self.accounts = accounts if accounts is not None else {}
        self.name = name
        self.code = {}
        for acc_key in list(self.accounts):
            self.accounts[acc_key] = self.accounts[acc_key]

    def generate_header(self, comment_generated_file: str, license: str) -> list[str]:
        lines = []
        lines.append(f'// SPDX-License-Identifier: {license}')
        lines.append(comment_generated_file)
        lines.append(f'pragma solidity {self.SOLIDITY_VERSION};\n')
        lines.append('import { Vm } from "forge-std/Vm.sol";\n')
        return lines

    def generate_code_contract(self) -> list[str]:
        lines = []
        lines.append(f'contract {self.name}Code ' + '{')
        for code_alias, code in self.code.items():
            lines.append(f'\tbytes constant internal {code_alias}Code = hex{code!r};')
        lines.append('}')
        return lines

    def generate_main_contract(self) -> list[str]:
        lines = []
        lines.append('')

        lines.append(f'contract {self.name} is {self.name}Code ' + '{')
        # Appending the Test contract address
        lines.append('\t// Test contract address, 0x7FA9385bE102ac3EAc297483Dd6233D62b3e1496')
        lines.append('\taddress private constant FOUNDRY_TEST_ADDRESS = 0x7FA9385bE102ac3EAc297483Dd6233D62b3e1496;')
        # Appending the cheatcode address to be able to avoid extending `Test`
        lines.append('\t// Cheat code address, 0x7109709ECfa91a80626fF3989D68f67F5b1DD12D')
        lines.append('\taddress private constant VM_ADDRESS = address(uint160(uint256(keccak256("hevm cheat code"))));')
        lines.append('\tVm private constant vm = Vm(VM_ADDRESS);\n')

        # Appending variables for external addresses
        for acc_key in list(self.accounts):
            lines.append('\taddress internal constant ' + self.accounts[acc_key] + 'Address = ' + acc_key + ';')

        lines.append('\n')

        # Appending `recreateState()` function that consists of calling `vm.etch` and `vm.store` to recreate state for external computation
        lines.append('\tfunction recreateState() public {')

        lines.append('\t\tbytes32 slot;')
        lines.append('\t\tbytes32 value;')

        for command in self.commands:
            lines.append('\t\t' + command + ';')

        lines.append('\t}')

        lines.append('\n')

        # Appending `_notExternalAddress(address user)` function that consists of `vm.assume(user != <address found in this contract>)`
        lines.append('\tfunction _notExternalAddress(address user) public pure {')

        lines.append('\t\tvm.assume(user != FOUNDRY_TEST_ADDRESS);')
        lines.append('\t\tvm.assume(user != VM_ADDRESS);')

        for acc_key in list(self.accounts):
            lines.append('\t\tvm.assume(user != ' + self.accounts[acc_key] + 'Address);')

        lines.append('\t}')

        lines.append('}')
        return lines

    def generate_condensed_file(self, comment_generated_file: str, license: str) -> list[str]:
        lines = self.generate_header(comment_generated_file, license)
        lines += self.generate_code_contract()
        lines += self.generate_main_contract()
        return lines

    def generate_main_contract_file(self, comment_generated_file: str, license: str) -> list[str]:
        lines = self.generate_header(comment_generated_file, license)
        lines.append('import { ' + self.name + 'Code } from "./' + self.name + 'Code.sol";')
        lines += self.generate_main_contract()
        return lines

    def generate_code_contract_file(self, comment_generated_file: str, license: str) -> list[str]:
        lines = []
        lines.append(f'// SPDX-License-Identifier: {license}')
        lines.append(comment_generated_file)
        lines.append(f'pragma solidity {self.SOLIDITY_VERSION};\n')
        lines += self.generate_code_contract()
        return lines

    def add_account(self, addr: str) -> None:
        if addr not in list(self.accounts):
            acc_name = 'acc' + str(len(list(self.accounts)))
            self.accounts[addr] = acc_name

    def extend_with_state_diff(self, e: StateDiffEntry) -> None:
        if e.has_ignored_kind or e.reverted:
            return

        if e.is_create:
            self.add_account(e.account)
            acc_name = self.accounts[e.account]
            self.code[acc_name] = e.deployed_code[2:]
            self.commands.append(f'vm.etch({acc_name}Address, {acc_name}Code)')

        if e.updates_balance:
            self.add_account(e.account)
            acc_name = self.accounts[e.account]
            self.commands.append(f'vm.deal({acc_name}Address, {e.new_balance})')

        for update in e.storage_updates:
            self.add_account(update.address)
            acc_name = self.accounts[update.address]
            self.commands.append(f'slot = hex{update.slot[2:]!r}')
            self.commands.append(f'value = hex{update.value[2:]!r}')
            self.commands.append(f'vm.store({acc_name}Address, slot, value)')

    def extend_with_state_dump(self, e: StateDumpEntry) -> None:
        self.add_account(e.account)
        acc_name = self.accounts[e.account]

        if e.code:
            self.code[acc_name] = e.code[2:]
            self.commands.append(f'vm.etch({acc_name}Address, {acc_name}Code)')

        if e.balance:
            self.commands.append(f'vm.deal({acc_name}Address, {e.balance})')

        for pair in e.storage:
            self.commands.append(f'slot = hex{pair.slot[2:]!r}')
            self.commands.append(f'value = hex{pair.value[2:]!r}')
            self.commands.append(f'vm.store({acc_name}Address, slot, value)')


def foundry_state_load(options: LoadStateOptions, output_dir: Path) -> None:
    ensure_dir_path(output_dir)
    accounts = read_contract_names(options.contract_names) if options.contract_names else {}
    recreate_state_contract = RecreateState(name=options.name, accounts=accounts)
    if options.from_state_diff:
        access_entries = read_recorded_state_diff(options.accesses_file)
        for access in access_entries:
            recreate_state_contract.extend_with_state_diff(access)
    else:
        recorded_accounts = read_recorded_state_dump(options.accesses_file)
        for account in recorded_accounts:
            recreate_state_contract.extend_with_state_dump(account)

    main_file = output_dir / Path(options.name + '.sol')

    if not options.license.strip():
        raise ValueError('License cannot be empty or blank')

    if options.condense_state_diff:
        main_file.write_text(
            '\n'.join(recreate_state_contract.generate_condensed_file(options.comment_generated_file, options.license))
        )
    else:
        code_file = output_dir / Path(options.name + 'Code.sol')
        main_file.write_text(
            '\n'.join(
                recreate_state_contract.generate_main_contract_file(options.comment_generated_file, options.license)
            )
        )
        code_file.write_text(
            '\n'.join(
                recreate_state_contract.generate_code_contract_file(options.comment_generated_file, options.license)
            )
        )


def read_recorded_state_diff(state_file: Path) -> list[StateDiffEntry]:
    if not state_file.exists():
        raise FileNotFoundError(f'Account accesses dictionary file not found: {state_file}')
    accesses = json.loads(state_file.read_text())['accountAccesses']
    return [StateDiffEntry(_a) for _a in accesses]


def read_recorded_state_dump(state_file: Path) -> list[StateDumpEntry]:
    if not state_file.exists():
        raise FileNotFoundError(f'Account accesses dictionary file not found: {state_file}')
    accounts = json.loads(state_file.read_text())
    return [StateDumpEntry(account, accounts[account]) for account in list(accounts)]
