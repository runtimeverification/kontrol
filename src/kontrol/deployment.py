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

    def generate_main_contract_file(self, target_dir: str) -> list[str]:
        lines = self.generate_header()
        lines.append('import { ' + self.name + 'Code } from "' + str(target_dir) + '/' + self.name + 'Code.sol";')
        lines += self.generate_main_contract()
        return lines

    def generate_code_contract_file(self) -> list[str]:
        lines = self.generate_header()
        lines += self.generate_code_contract()
        return lines

    def add_account(self, addr: str) -> None:
        if addr not in list(self.accounts):
            acc_name = 'acc' + str(len(list(self.accounts)))
            self.accounts[addr] = acc_name

    def add_cheatcode(self, dct: dict) -> None:
        kind = dct['kind']
        account = dct['account']
        old_balance = dct['oldBalance']
        new_balance = dct['newBalance']
        deployed_code = dct['deployedCode']
        reverted = dct['reverted']
        storage_accesses = dct['storageAccesses']

        # Ignore the access and account accessed if its one of the following
        ignored_kinds = ['Balance, Extcodesize, Extcodehash, Extcodecopy']
        if kind in ignored_kinds or reverted:
            return

        if deployed_code != '0x' and kind == 'Create':
            self.add_account(account)
            acc_name = self.accounts[account]
            self.code[acc_name] = deployed_code[2:]
            self.commands.append(f'vm.etch({acc_name}Address, {acc_name}Code)')

        if new_balance != old_balance:
            self.add_account(account)
            acc_name = self.accounts[account]
            self.commands.append(f'vm.deal({acc_name}Address, {new_balance})')

        for storage_access in storage_accesses:
            account_storage = storage_access['account']
            slot = storage_access['slot']
            is_write = storage_access['isWrite']
            previous_value = storage_access['previousValue']
            new_value = storage_access['newValue']
            reverted = storage_access['reverted']

            if reverted or not is_write or new_value == previous_value:
                continue

            self.add_account(account_storage)
            acc_name = self.accounts[account]
            self.commands.append(f'slot = hex{slot[2:]!r}')
            self.commands.append(f'value = hex{new_value[2:]!r}')
            self.commands.append(f'vm.store({acc_name}Address, slot, value)')
