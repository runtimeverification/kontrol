
import logging
import pprint
import json

from pathlib import Path
from typing import TYPE_CHECKING
from collections import deque
from typing import Any

from pyk.prelude.kbool import FALSE, TRUE, notBool
from pyk.prelude.bytes import bytesToken
from pyk.prelude.collections import map_empty, list_empty, set_empty
from pyk.kast.manip import set_cell
from pyk.cterm import CTerm
from pyk.ktool.krun import KRun
from pyk.rpc.rpc import JsonRpcServer, ServeRpcOptions
from pyk.kast.inner import KInner, KSort, KApply, KToken, KSequence, KVariable, Subst
from pyk.kdist import kdist
from kevm_pyk.kevm import KEVM

from .foundry import Foundry


from pyk.prelude.kint import intToken

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

        dir_path = Path(f"{kdist.kdist_dir}/kontrol/foundry")
        self.krun = KRun(dir_path)
        
        self._init_cterm()

    def exec_get_chain_id(self) -> int:
        cell = self.cterm.cell('CHAINID_CELL')
        return int(cell.token)
    
    def exec_get_memory_used(self) -> int:
        cell = self.cterm.cell('MEMORYUSED_CELL')
        return int(cell.token)

    def exec_get_gas_price(self) -> int:
        cell = self.cterm.cell('GASPRICE_CELL')
        return int(cell.token)
    
    def exec_get_block_number(self) -> int:
        cell = self.cterm.cell('NUMBER_CELL')
        return int(cell.token)
    
    def exec_get_balance(self, address: str) -> str:
        acctID = _address_to_accID(address)
        accounts_dict = self._get_all_accounts_dict()
        return hex(int(accounts_dict[str(acctID)]['<balance>'])).lower()

    def exec_accounts(self) -> list[str]:
        accounts_list = []
        
        for key in self._get_all_accounts_dict():
            accounts_list.append(_accID_to_address(int(key))) 

        return accounts_list

    def exec_add_account(self, address: str, balance_hex: str) -> None:
        acct_ID = _address_to_accID(address)
        balance = int(balance_hex, 16)
        new_account = KEVM.account_cell(
            intToken(acct_ID),
            intToken(balance),
            bytesToken(b""),
            map_empty(),
            map_empty(),
            intToken(0),
        )

        accounts_cell = self.cterm.cell('ACCOUNTS_CELL')
        new_accounts_cell = KApply('_AccountCellMap_', [accounts_cell, new_account])
        self.cterm = CTerm.from_kast(
            set_cell(self.cterm.config, 'ACCOUNTS_CELL', new_accounts_cell)
        )

    def exec_request_value(self) -> int:
        self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'K_CELL', KApply('kontrol_requestValue', [])))
        pattern = self.krun.kast_to_kore(self.cterm.config, sort=KSort('GeneratedTopCell'))
        output_kore = self.krun.run_pattern(pattern, pipe_stderr=False)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))
        rpc_response_cell = self.cterm.cell('RPCRESPONSE_CELL')
        _PPRINT.pprint(rpc_response_cell)
        return 0
    

    def exec_send_transaction(self, transaction_json: dict) -> int:

        fromAcct = transaction_json['from'] if "from" in transaction_json else None
        from_account_data = self._get_account_cell_by_address(fromAcct) 
        if(from_account_data is None):
            return -1

        txType   = transaction_json['type'] if "type" in transaction_json else "Legacy"
        toAcct   = transaction_json['to']   if "to" in transaction_json else "0x0"
        nonce    = int(transaction_json['nonce'], 16) if "nonce" in transaction_json else int(from_account_data['<nonce>'])
        gas      = int(transaction_json['gas'], 16) if "gas" in transaction_json else "0x15f90" #90000
        gasPrice = int(transaction_json['gasPrice'], 16) if "gasPrice" in transaction_json else "0x0"
        value    = int(transaction_json['value'], 16) if "value" in transaction_json else "0x0"
        data     = transaction_json['data'] if "data" in transaction_json else "0x0"

        if(toAcct is None):
            pass #contract deployment
    
        # _PPRINT.pprint(intToken(_address_to_accID(fromAcct)))
        self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'K_CELL', 
                        KApply('eth_sendTransaction', 
                        [
                            KToken(token=txType, sort=KSort(name='TxType')),
                            intToken(_address_to_accID(fromAcct)),
                            intToken(_address_to_accID(toAcct)),
                            intToken(gas),
                            intToken(gasPrice),
                            intToken(value),
                            intToken(nonce),
                            bytesToken(bytes.fromhex(data[2:]))
                        ])))

        pattern = self.krun.kast_to_kore(self.cterm.config, sort=KSort('GeneratedTopCell'))    
        output_kore = self.krun.run_pattern(pattern, pipe_stderr=False)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))
        rpc_response_cell = self.cterm.cell('RPCRESPONSE_CELL')
        _PPRINT.pprint(rpc_response_cell)
    
    # ------------------------------------------------------
    # VM data fetch helper functions
    # ------------------------------------------------------

    def _get_account_cell_by_address(self, address : str):
        acctId = _address_to_accID(address)
        accounts_dict = self._get_all_accounts_dict()
        account_data = accounts_dict[str(acctId)] if str(acctId) in accounts_dict else None
        return account_data

    def _get_all_accounts_dict(self) -> dict:
        cells = self.cterm.cells
        cell = cells.get('ACCOUNTS_CELL', None)

        accounts_dict = {}

        queue: deque[KInner] = deque(cell.args)
        while len(queue) > 0:
            account_cell = queue.popleft()
            if isinstance(account_cell, KApply):
                if account_cell.label.name == "<account>":
                    account_dict = {}
                    for args in account_cell.args: 
                        cell_name = args.label.name 
                        if(isinstance(args.args[0], KToken)):
                            account_dict[cell_name] = args.args[0].token

                    accounts_dict[account_dict['<acctID>']] = account_dict
                elif "AccountCellMap" in account_cell.label.name:
                    queue.extend(account_cell.args)

        return accounts_dict


    # ------------------------------------------------------
    # VM setup functions
    # ------------------------------------------------------

    def _create_initial_account_list(self) -> list[KInner]:
        initial_account_address = 645326474426547203313410069153905908525362434350
        init_account_list: list[KInner]= []
        number_of_sample_accounts = 2

        # Adding a zero address
        init_account_list.append(KEVM.account_cell(
            intToken(0),
            intToken(0),
            bytesToken(b""),
            map_empty(),
            map_empty(),
            intToken(0),
        ))

        # Adding sample addresses on the network
        for i in range(number_of_sample_accounts):
            init_account_list.append(KEVM.account_cell(
                intToken(initial_account_address + i),
                intToken(10**10),
                bytesToken(b""),
                map_empty(),
                map_empty(),
                intToken(0),
            ))

        # Adding the Foundry cheatcode address
        init_account_list.append(Foundry.account_CHEATCODE_ADDRESS(map_empty()))

        return init_account_list

    def _init_cterm(self) -> None:
        schedule = KApply('SHANGHAI_EVM')
        empty_config = self.krun.definition.empty_config(KSort('GeneratedTopCell'))
    
        init_accounts_list = self._create_initial_account_list()

        init_subst = {
            "K_CELL": KSequence([KEVM.sharp_execute()]), #, KVariable("CONTINUATION")]),
            "EXIT_CODE_CELL": intToken(1),
            "MODE_CELL": KToken(token="NOGAS", sort=KSort(name="Mode")),
            "SCHEDULE_CELL": schedule,
            "USEGAS_CELL": FALSE,
            "OUTPUT_CELL": bytesToken(b""),
            "STATUSCODE_CELL": KApply("EVMC_SUCCESS_NETWORK_EndStatusCode"),
            "CALLSTACK_CELL": list_empty(),
            "INTERIMSTATES_CELL": list_empty(),
            "TOUCHEDACCOUNTS_CELL": set_empty(), 
            "PROGRAM_CELL": intToken(0), 
            "JUMPDESTS_CELL": set_empty(), 
            "ID_CELL": Foundry.address_TEST_CONTRACT(),
            "CALLER_CELL": intToken(0), 
            "CALLDATA_CELL": intToken(0),
            "CALLVALUE_CELL": intToken(0),
            "WORDSTACK_CELL": KApply(".WordStack_EVM-TYPES_WordStack"),
            "LOCALMEM_CELL": bytesToken(b""),
            "PC_CELL": intToken(0),
            "GAS_CELL": intToken(0),
            "MEMORYUSED_CELL": intToken(0),
            "CALLGAS_CELL": intToken(0),
            "STATIC_CELL": FALSE,
            "CALLDEPTH_CELL": intToken(0),
            "SELFDESTRUCT_CELL": set_empty(),
            "LOG_CELL": list_empty(),
            "REFUND_CELL": intToken(0),
            "ACCESSEDACCOUNTS_CELL": set_empty(),
            "ACCESSEDSTORAGE_CELL": map_empty(),
            "GASPRICE_CELL": intToken(0),
            "ORIGIN_CELL": intToken(0),
            "BLOCKHASHES_CELL": list_empty(),
            "CHAINID_CELL": intToken(0),
            "ACCOUNTS_CELL": KEVM.accounts(init_accounts_list),
            "ACTIVE_CELL": FALSE,
            "DEPTH_CELL": intToken(0),
            "SINGLECALL_CELL": FALSE,
            "ISREVERTEXPECTED_CELL": FALSE,
            "ISOPCODEEXPECTED_CELL": FALSE,
            "RECORDEVENT_CELL": FALSE,
            "ISEVENTEXPECTED_CELL": FALSE,
            "ISCALLWHITELISTACTIVE_CELL": FALSE,
            "ISSTORAGEWHITELISTACTIVE_CELL": FALSE,
            "ADDRESSSET_CELL": set_empty(),
            "STORAGESLOTSET_CELL": set_empty(),
            "MOCKCALLS_CELL": KApply(".MockCallCellMap"),
            "ACTIVETRACING_CELL": FALSE,
            "RECORDEDTRACE_CELL": FALSE,
            "TRACESTORAGE_CELL": FALSE,
            "TRACEWORDSTACK_CELL": FALSE,
            "TRACEMEMORY_CELL": FALSE,
            "TRACEDATA_CELL": FALSE,
            "RPCREQUEST_CELL": intToken(0),
            "GENERATEDCOUNTER_CELL": intToken(0),
            "EXITCODE_CELL": intToken(0),
            "PREVIOUSHASH_CELL": intToken(0),
            "OMMERSHASH_CELL": intToken(0),
            "COINBASE_CELL": intToken(0),
            "STATEROOT_CELL": intToken(0),
            "TRANSACTIONSROOT_CELL": intToken(0),
            "RECEIPTSROOT_CELL": intToken(0),
            "LOGSBLOOM_CELL": bytesToken(b""),
            "DIFFICULTY_CELL": intToken(0),
            "NUMBER_CELL": intToken(0),
            "GASLIMIT_CELL": intToken(0),
            "GASUSED_CELL": intToken(0),
            "TIMESTAMP_CELL": intToken(0),
            "EXTRADATA_CELL": bytesToken(b""),
            "MIXHASH_CELL": intToken(0),
            "BLOCKNONCE_CELL": intToken(0),
            "BASEFEE_CELL": intToken(0),
            "WITHDRAWALSROOT_CELL": intToken(0),
            "OMMERBLOCKHEADERS_CELL": list_empty(),
            "TXORDER_CELL": list_empty(),
            "TXPENDING_CELL": list_empty(),
            "MESSAGES_CELL": map_empty(),
            "EXPECTEDREASON_CELL": bytesToken(b""),
            "EXPECTEDDEPTH_CELL": intToken(0),
            "EXPECTEDVALUE_CELL": intToken(0),
            "EXPECTEDDATA_CELL": bytesToken(b""),
            "CHECKEDTOPICS_CELL": list_empty(),
            "CHECKEDDATA_CELL": FALSE,
            "RPCRESPONSE_CELL": intToken(0),
            "PREVCALLER_CELL": init_accounts_list[0],
            "PREVORIGIN_CELL": init_accounts_list[0],
            "NEWCALLER_CELL": init_accounts_list[0],
            "NEWORIGIN_CELL": init_accounts_list[0],
            "EXPECTEDADDRESS_CELL": init_accounts_list[0],
            "OPCODETYPE_CELL": intToken(0),
            "EXPECTEDEVENTADDRESS_CELL": init_accounts_list[0],
        }

        init_term = Subst(init_subst)(empty_config)
        self.cterm = CTerm.from_kast(init_term)



# ------------------------------------------------------
# Helpers
# ------------------------------------------------------
def _set_cell(cterm: CTerm, cell: str, value: Any, sort: str) -> None:
    cterm = CTerm.from_kast(
        set_cell(cterm.config, cell, KToken(token=str(value), sort=KSort(name=sort)))
    )

def _accID_to_address(accID: int) -> str:
    hex_value = hex(accID).lower()[2:]
    target_length = 40
    padding_length = target_length - len(hex_value)
    padded_address = "0" * padding_length + hex_value
    return "0x" + padded_address


def _address_to_accID(address: str) -> int:
    try:
        return int(address, 16)
    except ValueError:
        print(f"Invalid hexadecimal string: {address}")
        return None

