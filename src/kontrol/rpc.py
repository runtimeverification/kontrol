from __future__ import annotations

import pprint
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kevm_pyk.kevm import KEVM
from pyk.cterm import CTerm
from pyk.kast.inner import KApply, KSequence, KSort, KToken, Subst
from pyk.kast.manip import set_cell
from pyk.kdist import kdist
from pyk.ktool.krun import KRun
from pyk.prelude.bytes import bytesToken
from pyk.prelude.collections import map_empty
from pyk.prelude.k import GENERATED_TOP_CELL
from pyk.prelude.kbool import TRUE
from pyk.prelude.kint import intToken
from pyk.rpc.rpc import JsonRpcServer

from .foundry import Foundry

if TYPE_CHECKING:
    from pyk.kast.inner import KInner
    from pyk.rpc.rpc import ServeRpcOptions

_PPRINT = pprint.PrettyPrinter(width=41, compact=True)


class StatefulKJsonRpcServer(JsonRpcServer):
    krun: KRun
    cterm: CTerm

    def __init__(self, options: ServeRpcOptions) -> None:
        super().__init__(options)

        self.register_method('eth_chainId', self.exec_get_chain_id)
        self.register_method('eth_memoryUsed', self.exec_get_memory_used)
        self.register_method('eth_gasPrice', self.exec_get_gas_price)
        self.register_method('eth_blockNumber', self.exec_get_block_number)
        self.register_method('eth_accounts', self.exec_accounts)
        self.register_method('eth_getBalance', self.exec_get_balance)
        self.register_method('eth_sendTransaction', self.exec_send_transaction)
        self.register_method('kontrol_requestValue', self.exec_request_value)
        self.register_method('kontrol_addAccount', self.exec_add_account)

        dir_path = Path(f'{kdist.kdist_dir}/kontrol/foundry')
        self.krun = KRun(dir_path)

        self._init_cterm()

    def exec_get_chain_id(self) -> int:
        cell = self.cterm.cell('CHAINID_CELL')
        assert type(cell) is KToken
        return int(cell.token)

    def exec_get_memory_used(self) -> int:
        cell = self.cterm.cell('MEMORYUSED_CELL')
        assert type(cell) is KToken
        return int(cell.token)

    def exec_get_gas_price(self) -> int:
        cell = self.cterm.cell('GASPRICE_CELL')
        assert type(cell) is KToken
        return int(cell.token)

    def exec_get_block_number(self) -> int:
        cell = self.cterm.cell('NUMBER_CELL')
        assert type(cell) is KToken
        return int(cell.token)

    def exec_get_balance(self, address: str) -> str:
        acct_id = _address_to_acct_id(address)
        accounts_dict = self._get_all_accounts_dict()
        return hex(int(accounts_dict[str(acct_id)]['<balance>'])).lower()

    def exec_accounts(self) -> list[str]:
        accounts_list = []

        for key in self._get_all_accounts_dict():
            accounts_list.append(_acct_id_to_address(int(key)))

        return accounts_list

    def exec_add_account(self, address: str, balance_hex: str) -> None:
        acct_id = _address_to_acct_id(address)

        balance = int(balance_hex, 16)
        new_account = KEVM.account_cell(
            intToken(acct_id),
            intToken(balance),
            bytesToken(b''),
            map_empty(),
            map_empty(),
            intToken(0),
        )

        accounts_cell = self.cterm.cell('ACCOUNTS_CELL')
        new_accounts_cell = KApply('_AccountCellMap_', [accounts_cell, new_account])
        self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'ACCOUNTS_CELL', new_accounts_cell))

    def exec_request_value(self) -> int:
        self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'K_CELL', KApply('kontrol_requestValue', [])))
        pattern = self.krun.kast_to_kore(self.cterm.config, sort=GENERATED_TOP_CELL)
        output_kore = self.krun.run_pattern(pattern, pipe_stderr=False)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))
        rpc_response_cell = self.cterm.cell('RPCRESPONSE_CELL')
        _PPRINT.pprint(rpc_response_cell)
        return 0

    def exec_send_transaction(self, transaction_json: dict) -> int:

        from_acct = transaction_json['from'] if 'from' in transaction_json else None
        from_account_data = self._get_account_cell_by_address(from_acct)
        if from_account_data is None:
            return -1

        tx_type = transaction_json['type'] if 'type' in transaction_json else 'Legacy'
        to_acct = transaction_json['to'] if 'to' in transaction_json else '0x0'
        nonce = int(transaction_json['nonce'], 16) if 'nonce' in transaction_json else int(from_account_data['<nonce>'])
        gas = int(transaction_json['gas'], 16) if 'gas' in transaction_json else 90000  #'0x15f90'
        gas_price = int(transaction_json['gasPrice'], 16) if 'gasPrice' in transaction_json else 0  #'0x0'
        value = int(transaction_json['value'], 16) if 'value' in transaction_json else 0  #'0x0'
        data = transaction_json['data'] if 'data' in transaction_json else '0x0'

        if to_acct is None:
            pass  # contract deployment

        # _PPRINT.pprint(intToken(_address_to_acct_id(from_acct)))
        self.cterm = CTerm.from_kast(
            set_cell(
                self.cterm.config,
                'K_CELL',
                KApply(
                    'eth_sendTransaction',
                    [
                        KApply(tx_type + '_EVM-TYPES_TxType'),
                        intToken(_address_to_acct_id(from_acct)),
                        intToken(_address_to_acct_id(to_acct)),
                        intToken(gas),
                        intToken(gas_price),
                        intToken(value),
                        intToken(nonce),
                        bytesToken(bytes.fromhex(data[2:])),
                    ],
                ),
            )
        )

        pattern = self.krun.kast_to_kore(self.cterm.config, sort=GENERATED_TOP_CELL)
        output_kore = self.krun.run_pattern(pattern, pipe_stderr=False)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))
        rpc_response_cell = self.cterm.cell('RPCRESPONSE_CELL')
        _PPRINT.pprint(rpc_response_cell)
        assert type(rpc_response_cell) is KToken
        return int(rpc_response_cell.token)

    # ------------------------------------------------------
    # VM data fetch helper functions
    # ------------------------------------------------------

    def _get_account_cell_by_address(self, address: str) -> dict:
        acct_id = _address_to_acct_id(address)
        accounts_dict = self._get_all_accounts_dict()
        account_data = accounts_dict[str(acct_id)] if str(acct_id) in accounts_dict else None
        return account_data

    def _get_all_accounts_dict(self) -> dict:
        cells = self.cterm.cells
        cell = cells.get('ACCOUNTS_CELL', None)
        assert type(cell) is KApply

        accounts_dict = {}

        queue: deque[KInner] = deque(cell.args)
        while len(queue) > 0:
            account_cell = queue.popleft()
            if isinstance(account_cell, KApply):
                if account_cell.label.name == '<account>':
                    account_dict = {}
                    for args in account_cell.args:
                        assert type(args) is KApply
                        cell_name = args.label.name
                        if isinstance(args.args[0], KToken):
                            account_dict[cell_name] = args.args[0].token

                    accounts_dict[account_dict['<acctID>']] = account_dict
                elif 'AccountCellMap' in account_cell.label.name:
                    queue.extend(account_cell.args)

        return accounts_dict

    # ------------------------------------------------------
    # VM setup functions
    # ------------------------------------------------------

    def _create_initial_account_list(self) -> list[KInner]:
        initial_account_address = 645326474426547203313410069153905908525362434350
        init_account_list: list[KInner] = []
        number_of_sample_accounts = 2

        # Adding a zero address
        init_account_list.append(
            KEVM.account_cell(
                intToken(0),
                intToken(0),
                bytesToken(b''),
                map_empty(),
                map_empty(),
                intToken(0),
            )
        )

        # Adding sample addresses on the network
        for i in range(number_of_sample_accounts):
            init_account_list.append(
                KEVM.account_cell(
                    intToken(initial_account_address + i),
                    intToken(10**10),
                    bytesToken(b''),
                    map_empty(),
                    map_empty(),
                    intToken(0),
                )
            )

        # Adding the Foundry cheatcode address
        init_account_list.append(Foundry.account_CHEATCODE_ADDRESS(map_empty()))

        return init_account_list

    def _init_cterm(self) -> None:
        KApply('SHANGHAI_EVM')
        self.krun.definition.empty_config(GENERATED_TOP_CELL)

        init_accounts_list = self._create_initial_account_list()

        init_config = self.krun.definition.init_config(GENERATED_TOP_CELL)

        init_subst = {
            '$PGM': KSequence([KEVM.sharp_execute()]),
            '$MODE': KApply('NORMAL'),
            '$SCHEDULE': KApply('SHANGHAI_EVM'),
            '$USEGAS': TRUE,
            '$CHAINID': intToken(0),
        }

        init_config = set_cell(init_config, 'ACCOUNTS_CELL', KEVM.accounts(init_accounts_list))

        init_term = Subst(init_subst)(init_config)
        self.cterm = CTerm.from_kast(init_term)


# ------------------------------------------------------
# Helpers
# ------------------------------------------------------
def _set_cell(cterm: CTerm, cell: str, value: Any, sort: str) -> None:
    cterm = CTerm.from_kast(set_cell(cterm.config, cell, KToken(token=str(value), sort=KSort(name=sort))))


def _acct_id_to_address(acct_id: int) -> str:
    hex_value = hex(acct_id).lower()[2:]
    target_length = 40
    padding_length = target_length - len(hex_value)
    padded_address = '0' * padding_length + hex_value
    return '0x' + padded_address


def _address_to_acct_id(address: str) -> int:
    try:
        return int(address, 16)
    except ValueError:
        print(f'Invalid hexadecimal string: {address}')
        return -1  # TODO: Trigger error instead of returning value
