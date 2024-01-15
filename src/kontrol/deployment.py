from typing import NamedTuple


class StorageUpdate(NamedTuple):
    address: str
    slot: str
    value: str


class SummaryEntry:
    kind: str
    account: str
    old_balance: int
    new_balance: int
    deployed_code: str
    reverted: bool
    storage_updates: list[StorageUpdate]

    def __init__(self, e: dict) -> None:
        self.kind = e['kind']
        self.account = e['account']
        self.old_balance = e['oldBalance']
        self.new_balance = e['newBalance']
        self.deployed_code = e['deployedCode']
        self.reverted = e['reverted']
        storage_changes = []
        for storage_access in e['storageAccesses']:
            account_storage = storage_access['account']
            slot = storage_access['slot']
            is_write = storage_access['isWrite']
            previous_value = storage_access['previousValue']
            new_value = storage_access['newValue']
            reverted = storage_access['reverted']

            if reverted or not is_write or new_value == previous_value:
                continue

            storage_changes.append(StorageUpdate(account_storage, slot, new_value))
        self.storage_updates = storage_changes

    @property
    def has_ignored_kind(self) -> bool:
        return self.kind in ['Balance', 'Extcodesize', 'Extcodehash', 'Extcodecopy']

    @property
    def is_create(self) -> bool:
        return self.deployed_code != '0x' and self.kind == 'Create'

    @property
    def updates_balance(self) -> bool:
        return self.new_balance != self.old_balance


class DeploymentSummary:
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

    def generate_header(self) -> list[str]:
        lines = []
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
        # Appending the cheatcode address to be able to avoid extending `Test`
        lines.append('\t// Cheat code address, 0x7109709ECfa91a80626fF3989D68f67F5b1DD12D')
        lines.append(
            '\taddress internal constant VM_ADDRESS = address(uint160(uint256(keccak256("hevm cheat code"))));'
        )
        lines.append('\tVm internal constant vm = Vm(VM_ADDRESS);\n')

        for acc_key in list(self.accounts):
            lines.append('\taddress internal constant ' + self.accounts[acc_key] + 'Address = ' + acc_key + ';')

        lines.append('\n')

        lines.append('\tfunction recreateDeployment() public {')

        lines.append('\t\tbytes32 slot;')
        lines.append('\t\tbytes32 value;')

        for command in self.commands:
            lines.append('\t\t' + command + ';')

        lines.append('\t}')

        lines.append('}')
        return lines

    def generate_condensed_file(self) -> list[str]:
        lines = self.generate_header()
        lines += self.generate_code_contract()
        lines += self.generate_main_contract()
        return lines

    def generate_main_contract_file(self) -> list[str]:
        lines = self.generate_header()
        lines.append('import { ' + self.name + 'Code } from "./' + self.name + 'Code.sol";')
        lines += self.generate_main_contract()
        return lines

    def generate_code_contract_file(self) -> list[str]:
        lines = []
        lines.append(f'pragma solidity {self.SOLIDITY_VERSION};\n')
        lines += self.generate_code_contract()
        return lines

    def add_account(self, addr: str) -> None:
        if addr not in list(self.accounts):
            acc_name = 'acc' + str(len(list(self.accounts)))
            self.accounts[addr] = acc_name

    def extend(self, e: SummaryEntry) -> None:
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
