from __future__ import annotations

import ast
import pprint
from collections import deque
from datetime import datetime
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
from pyk.prelude.string import stringToken
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
        self.register_method('eth_getBlockByNumber', self.exec_get_block_by_number)
        self.register_method('eth_accounts', self.exec_accounts)
        self.register_method('eth_getBalance', self.exec_get_balance)
        self.register_method('eth_sendTransaction', self.exec_send_transaction)
        self.register_method('eth_getTransactionByHash', self.exec_get_transaction_by_hash)
        self.register_method('eth_getTransactionReceipt', self.exec_get_transaction_receipt)
        self.register_method('kontrol_requestValue', self.exec_request_value)
        self.register_method('kontrol_addAccount', self.exec_add_account)

        dir_path = Path(f'{kdist.kdist_dir}/kontrol/foundry')
        self.krun = KRun(dir_path)

        start_time = datetime.now()

        self._init_cterm()

        end_time = datetime.now()

        print(f'Server initialization finished in {(end_time - start_time).total_seconds()} seconds.')

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

    def exec_get_block_by_number(self, block_number: int) -> int:

        print(f'BLOCK NUMBER: {block_number}')

        self._get_all_block_storage_dict()

        return block_number

    def exec_get_balance(self, address: str) -> str:
        acct_id = _address_to_acct_id(address)
        accounts_dict = self._get_all_accounts_dict()
        return hex(int(accounts_dict[str(acct_id)]['<balance>'])).lower()

    def exec_accounts(self) -> list[str]:
        accounts_list = []

        for key in self._get_all_accounts_dict():
            accounts_list.append(_acct_id_to_address(int(key)))

        return accounts_list

    def exec_add_account(self, private_key: str, balance_hex: str) -> None:
        balance = int(balance_hex, 16)
        self.cterm = CTerm.from_kast(
            set_cell(
                self.cterm.config, 'K_CELL', KApply('acctFromPrivateKey', [stringToken(private_key), intToken(balance)])
            )
        )
        pattern = self.krun.kast_to_kore(self.cterm.config, sort=GENERATED_TOP_CELL)
        output_kore = self.krun.run_pattern(pattern, pipe_stderr=True)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))
        return None

    def exec_request_value(self) -> int:
        self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'K_CELL', KApply('kontrol_requestValue', [])))
        pattern = self.krun.kast_to_kore(self.cterm.config, sort=GENERATED_TOP_CELL)
        output_kore = self.krun.run_pattern(pattern, pipe_stderr=True)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))
        rpc_response_cell = self.cterm.cell('RPCRESPONSE_CELL')
        _PPRINT.pprint(rpc_response_cell)
        return 0

    def exec_send_transaction(self, transaction_json: dict) -> str:

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
        output_kore = self.krun.run_pattern(pattern, pipe_stderr=True)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))

        # print('K----------------------------------------------')
        # k_cell = self.cterm.cell('K_CELL')
        # _PPRINT.pprint(k_cell)
        # print('TXORDER----------------------------------------------')
        # tx_order_cell = self.cterm.cell('TXORDER_CELL')
        # _PPRINT.pprint(tx_order_cell)
        # print('RPCRESPONSE----------------------------------------------')
        # rpc_response_cell = self.cterm.cell('RPCRESPONSE_CELL')
        # _PPRINT.pprint(rpc_response_cell)

        return self._get_last_message_tx_hash()

    def exec_get_transaction_by_hash(self, tx_hash: str) -> dict | str:
        tx_receipt = self._get_tx_receipt_by_hash(tx_hash)

        if tx_receipt is None:
            return 'Transaction receipt not found'

        msg_id = str(tx_receipt['<txID>'])
        messages_dict = self._get_all_messages_dict()

        if msg_id not in messages_dict:
            return 'Transaction not found.'

        formatted_messages_dict = _apply_format_to_message_cell_json_dict(messages_dict[msg_id])
        formatted_messages_dict['blockNumber'] = tx_receipt['<txBlockNumber>']
        formatted_messages_dict['hash'] = tx_receipt['<txHash>']
        formatted_messages_dict['from'] = _acct_id_to_address(tx_receipt['<sender>'])
        del formatted_messages_dict['priorityFee']
        del formatted_messages_dict['maxFee']
        return formatted_messages_dict

    def exec_get_transaction_receipt(self, tx_hash: str) -> dict | str:
        tx_receipt_dict = self._get_tx_receipt_by_hash(tx_hash)

        if tx_receipt_dict is None:
            return 'Transaction receipt not found'

        msg_id = str(tx_receipt_dict['<txID>'])
        messages_dict = self._get_all_messages_dict()

        if msg_id not in messages_dict:
            return 'Transaction not found.'

        formatted_receipt_dict = _apply_format_to_message_cell_json_dict(tx_receipt_dict)
        formatted_receipt_dict['to'] = messages_dict[msg_id]['<to>']
        formatted_receipt_dict['transactionHash'] = formatted_receipt_dict['hash']
        formatted_receipt_dict['from'] = formatted_receipt_dict['sender']
        del formatted_receipt_dict['hash']
        del formatted_receipt_dict['sender']
        del formatted_receipt_dict['bloomFilter']
        del formatted_receipt_dict['nonce']

        return formatted_receipt_dict

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

    def _get_tx_receipt_by_msg_id(self, msg_id: int) -> dict | None:
        tx_receipts_dict = self._get_all_tx_receipts_dict()
        tx_receipt = None

        for tx_receipt_key in tx_receipts_dict:
            if tx_receipts_dict[tx_receipt_key]['<txID>'] == msg_id:
                tx_receipt = tx_receipts_dict[tx_receipt_key]

        return tx_receipt

    def _get_tx_receipt_by_hash(self, hash: str) -> dict | None:
        tx_receipts_dict = self._get_all_tx_receipts_dict()
        return tx_receipts_dict[hash[2:]]

    def _get_all_tx_receipts_dict(self) -> dict:
        cells = self.cterm.cells
        cell = cells.get('TXRECEIPTS_CELL', None)

        tx_receipts_dict = {}

        if cell is None:
            # For the first transaction, the cells of the message will be scattered in the model, and if there is only this transaction in the messages map, this dictionary entry must be built manually.
            cell = self.cterm.cell('TXHASH_CELL')
            assert type(cell) is KToken
            tx_hash = ast.literal_eval(cell.token).hex()

            tx_receipts_dict[tx_hash] = {'<txHash>': '0x' + tx_hash}

            cell = self.cterm.cell('TXCUMULATIVEGAS_CELL')
            assert type(cell) is KToken
            tx_receipts_dict[tx_hash]['<txNonce>'] = int(cell.token)
            cell = self.cterm.cell('BLOOMFILTER_CELL')
            assert type(cell) is KToken
            tx_receipts_dict[tx_hash]['<bloomFilter>'] = '0x' + ast.literal_eval(cell.token).hex()
            cell = self.cterm.cell('TXSTATUS_CELL')
            assert type(cell) is KToken
            tx_receipts_dict[tx_hash]['<txStatus>'] = int(cell.token)
            cell = self.cterm.cell('TXID_CELL')
            assert type(cell) is KToken
            tx_receipts_dict[tx_hash]['<txID>'] = int(cell.token)
            cell = self.cterm.cell('SENDER_CELL')
            assert type(cell) is KToken
            tx_receipts_dict[tx_hash]['<sender>'] = int(cell.token)
            cell = self.cterm.cell('TXBLOCKNUMBER_CELL')
            assert type(cell) is KToken
            tx_receipts_dict[tx_hash]['<txBlockNumber>'] = int(cell.token)

        else:
            assert type(cell) is KApply
            queue: deque[KInner] = deque(cell.args)
            while len(queue) > 0:
                tx_receipt_cell = queue.popleft()
                if isinstance(tx_receipt_cell, KApply):
                    if tx_receipt_cell.label.name == '<txReceipt>':
                        tx_receipt_dict = {}
                        for args in tx_receipt_cell.args:
                            assert type(args) is KApply
                            cell_name = args.label.name
                            if isinstance(args.args[0], KToken):
                                value = None

                                if args.args[0].token.isdecimal():
                                    value = int(args.args[0].token)
                                else:
                                    value = '0x' + ast.literal_eval(args.args[0].token).hex()

                                tx_receipt_dict[cell_name] = value

                        tx_receipts_dict[tx_receipt_dict['<txHash>']] = tx_receipt_dict
                    elif 'txReceiptCellMap' in tx_receipt_cell.label.name:
                        queue.extend(tx_receipt_cell.args)

        return tx_receipts_dict

    def _get_last_message_tx_hash(self) -> str:

        cell = self.cterm.cell('CURRENTTXID_CELL')
        assert type(cell) is KToken
        last_tx_id = int(cell.token) - 1

        tx_receipt = self._get_tx_receipt_by_msg_id(last_tx_id)

        assert tx_receipt is not None

        last_tx_hash = tx_receipt['<txHash>']  # _msg_id_to_tx_hash(last_tx_id)

        return last_tx_hash

    def _get_all_messages_dict(self) -> dict:
        messages_dict: dict[str, dict] = {}

        cells = self.cterm.cells
        cell = cells.get('MESSAGES_CELL', None)

        if cell is None:
            # For the first transaction, the cells of the message will be scattered in the model, and if there is only this transaction in the messages map, this dictionary entry must be built manually.
            cell = self.cterm.cell('MSGID_CELL')
            assert type(cell) is KToken
            msg_id = cell.token
            messages_dict[msg_id] = {}

            cell = self.cterm.cell('TXNONCE_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<txNonce>'] = int(cell.token)
            cell = self.cterm.cell('TXGASPRICE_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<txGasPrice>'] = int(cell.token)
            cell = self.cterm.cell('TXGASLIMIT_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<txGasLimit>'] = int(cell.token)
            cell = self.cterm.cell('TO_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<to>'] = _acct_id_to_address(int(cell.token))
            cell = self.cterm.cell('VALUE_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<value>'] = int(cell.token)
            cell = self.cterm.cell('SIGV_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<sigV>'] = int(cell.token)
            cell = self.cterm.cell('SIGR_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<sigR>'] = ast.literal_eval(cell.token).hex()
            cell = self.cterm.cell('SIGS_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<sigS>'] = ast.literal_eval(cell.token).hex()
            cell = self.cterm.cell('DATA_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<data>'] = '0x' + ast.literal_eval(cell.token).hex()
            cell = self.cterm.cell('TXCHAINID_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<txChainID>'] = int(cell.token)
            cell = self.cterm.cell('TXPRIORITYFEE_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<txPriorityFee>'] = int(cell.token)
            cell = self.cterm.cell('TXMAXFEE_CELL')
            assert type(cell) is KToken
            messages_dict[msg_id]['<txMaxFee>'] = int(cell.token)
        else:
            assert type(cell) is KApply
            queue: deque[KInner] = deque(cell.args)
            while len(queue) > 0:
                message_cell = queue.popleft()
                if isinstance(message_cell, KApply):
                    if message_cell.label.name == '<message>':
                        message_dict = {}
                        for args in message_cell.args:
                            assert type(args) is KApply
                            cell_name = str(args.label.name)
                            if isinstance(args.args[0], KToken):

                                value = None

                                if args.args[0].token.isdecimal():
                                    value = int(args.args[0].token)
                                else:
                                    value = '0x' + ast.literal_eval(args.args[0].token).hex()

                                message_dict[cell_name] = value

                        msg_id = str(message_dict['<msgID>'])
                        messages_dict[msg_id] = message_dict
                    elif 'MessageCellMap' in message_cell.label.name:
                        queue.extend(message_cell.args)

        return messages_dict

    def _get_all_block_storage_dict(self) -> dict:
        block_storage_dict = {}

        cell = self.cterm.cell('BLOCKSTORAGE_CELL')
        assert type(cell) is KApply

        queue: deque[KInner] = deque(cell.args)
        while len(queue) > 0:
            cell = queue.popleft()
            if isinstance(cell, KApply):
                # print(cell.label.name)
                if 'BlockchainItem' in cell.label.name:
                    item_dict = {}
                    for args in cell.args:
                        assert type(args) is KApply
                        cell_dict = _extract_cell_data(args)
                        item_dict[args.label.name] = cell_dict

                    # msg_id = str(message_dict['<network>'])
                    block_storage_dict[item_dict['<block>']['<number>']] = item_dict
                # elif 'Map' in cell.label.name:# or
                elif '_|->_' in cell.label.name:
                    queue.extend(cell.args)
                # else:
                #     print(cell.label.name)

        return block_storage_dict

    # ------------------------------------------------------
    # VM setup functions
    # ------------------------------------------------------

    def _add_initial_accounts(self) -> None:
        balance = 10**20

        private_keys = [
            '0xcdeac0dd5ec7c04072af48f2a4451e102a80ca5bb441a7b4d72c176cea61866e',
            '0xafdfd9c3d2095ef696594f6cedcae59e72dcd697e2a7521b1578140422a4f890',
        ]
        sequence_of_productions = []

        for private_key in private_keys:
            sequence_of_productions.append(KApply('acctFromPrivateKey', [stringToken(private_key), intToken(balance)]))

        sequence_of_kapplies = KSequence(sequence_of_productions)
        self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'K_CELL', sequence_of_kapplies))
        pattern = self.krun.kast_to_kore(self.cterm.config, sort=GENERATED_TOP_CELL)
        output_kore = self.krun.run_pattern(pattern, pipe_stderr=True)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))

        return None

    def _create_initial_account_list(self) -> list[KInner]:
        init_account_list: list[KInner] = []

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
        self._add_initial_accounts()


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


def _tx_hash_to_msg_id(hash: str) -> int:
    try:
        return int(hash, 16)
    except ValueError:
        print(f'Invalid hexadecimal string: {hash}')
        return -1  # TODO: Trigger error instead of returning value


def _apply_format_to_message_cell_json_dict(message_dict: dict) -> dict:
    formatted_message_dict = {}

    for key in message_dict:
        new_key = key.replace('<', '').replace('>', '').replace('sig', '').replace('tx', '')

        new_key = new_key[0].lower() + new_key[1:]

        if new_key == 'gasLimit':
            new_key = 'gas'
        elif new_key == 'data':
            new_key = 'input'

        if new_key == 'to':
            formatted_message_dict[new_key] = message_dict[key]
        else:
            value = message_dict[key]

            try:
                int(value, 16)
                value = '0x' + value if value[:2] != '0x' else value
            except Exception:
                if type(value) is int:
                    value = hex(value)
                elif message_dict[key].isdecimal():
                    value = hex(int(message_dict[key]))
                else:
                    value = '0x' + ast.literal_eval(message_dict[key]).hex()

            formatted_message_dict[new_key] = value

    return formatted_message_dict

def _is_label_a_map(name: str) -> bool:
    map_names = ['<accounts>', '<messages>', '<blocks>']
    
    if name in map_names:
        return True
    
    return False


def _extract_cell_data(cell: KApply):
    if(_is_label_a_map(cell.label.name)):
        return _from_cell_map_to_list(cell)
    
    return _convert_cell_to_dict(cell)

def _from_cell_map_to_list(cell: KApply):
    index_list = []
    cell_list = list(cell.args)
    
    index = 0
    for cell in cell_list:
        if('CellMap' in cell.label.name):
            index_list.append(index)
            for new_cell in list(cell.args):
                cell_list.append(new_cell)
        index += 1

    index_list.reverse()

    for index in index_list:
        cell_list.pop(index)

    return_list = []
    for cell in cell_list:
        return_list.append(_extract_cell_data(cell))

    return return_list


def _convert_cell_to_dict(cell: KApply, depth = 0) -> dict | int | str:
    cell_dict = {}
            
    for args in cell.args:

        if type(args) is not KToken:
            assert type(args) is KApply

            cell_dict[args.label.name] = _extract_cell_data(args)
        else:
            assert type(args) is KToken
            value = None
            if args.token.isdecimal():
                value = int(args.token)
            else:
                value = '0x' + ast.literal_eval(args.token).hex()

            return value

    return cell_dict
