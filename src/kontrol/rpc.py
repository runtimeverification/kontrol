
from pathlib import Path
from typing import TYPE_CHECKING
import logging
import pprint

from pyk.prelude.kbool import FALSE, TRUE, notBool
from pyk.prelude.bytes import bytesToken
from pyk.prelude.collections import map_empty, list_empty, set_empty
from pyk.kast.manip import set_cell
from pyk.cterm import CTerm
from pyk.ktool.krun import KRun
from pyk.rpc.rpc import JsonRpcServer, ServeRpcOptions
from pyk.kast.inner import KInner, KSort, KApply, KToken, KSequence, KVariable, Subst
from pyk.kdist import kdist

from typing import Any
from kevm_pyk.kevm import KEVM
from .foundry import Foundry

from pyk.prelude.kint import intToken

_PPRINT = pprint.PrettyPrinter(width=41, compact=True)

# Helpers
class StatefulKJsonRpcServer(JsonRpcServer):
    krun: KRun
    cterm: CTerm

    def __init__(self, options: ServeRpcOptions) -> None:
        super().__init__(options)

        self.register_method('eth_chainId', self.exec_get_chain_id)
        self.register_method('eth_memoryUsed', self.exec_get_memory_used)
        self.register_method('eth_gasPrice', self.exec_get_gas_price)
        self.register_method('eth_blockNumber', self.exec_get_block_number)
        # self.register_method('eth_getBalance', self.exec_get_balance)
        self.register_method('kontrol_addAccount', self.exec_add_account)

        if not options.definition_dir:
            raise ValueError('Must specify a definition dir with --definition')

        dir_path = Path("/home/acassimiro/.cache/kdist-889f2ce/kontrol/foundry")
        # self.krun = KRun(options.definition_dir)
        self.krun = KRun(dir_path)

        self._init_cterm()


    def exec_get_chain_id(self) -> int:
        cell = self.cterm.cell('CHAINID_CELL')
        _PPRINT.pprint(cell)
        return int(cell.token)
    
    def exec_get_memory_used(self) -> int:
        cell = self.cterm.cell('MEMORYUSED_CELL')
        _PPRINT.pprint(cell)
        return int(cell.token)

    def exec_get_gas_price(self) -> int:
        cell = self.cterm.cell('GASPRICE_CELL')
        _PPRINT.pprint(cell)
        return int(cell.token)
    
    def exec_get_block_number(self) -> int:
        cell = self.cterm.cell('NUMBER_CELL')
        _PPRINT.pprint(cell)
        return int(cell.token)


    def exec_add_account(self) -> int:
        self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'K_CELL', KApply('#eth_requestValue_KONTROL-VM_KItem', [])))
        pattern = self.krun.kast_to_kore(self.cterm.config, sort=KSort('GeneratedTopCell'))
        # pattern = self.krun.kast_to_kore(self.cterm.config, sort=Foundry.Sorts.SYMBOLIK_CELL)
        output_kore = self.krun.run_pattern(pattern)
        self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))

        rpc_response_cell = self.cterm.cell('RPCRESPONSE_CELL')
        _PPRINT.pprint(rpc_response_cell)
        return 0
    

    def _init_cterm(self) -> None:
        kevm = KEVM(kdist.get('kontrol.foundry'))
        schedule = KApply('SHANGHAI_EVM')
        empty_config = kevm.definition.empty_config(Foundry.Sorts.SYMBOLIK_CELL)
    
        init_subst = {
            "K_CELL": KSequence([KEVM.sharp_execute()]), #, KVariable("CONTINUATION")]),
            "EXIT_CODE_CELL": intToken(1),
            "MODE_CELL": KApply("NORMAL"),
            "SCHEDULE_CELL": schedule,
            "USEGAS_CELL": FALSE,
            "OUTPUT_CELL": bytesToken(b""),
            "STATUSCODE_CELL": KApply("EVMC_SUCCESS_NETWORK_EndStatusCode"), # KVariable("STATUSCODE"),
            "CALLSTACK_CELL": list_empty(),
            "INTERIMSTATES_CELL": list_empty(),
            "TOUCHEDACCOUNTS_CELL": set_empty(), 
            "PROGRAM_CELL": intToken(0), # program,
            "JUMPDESTS_CELL": set_empty(), # KEVM.compute_valid_jumpdests(program),
            "ID_CELL": Foundry.address_TEST_CONTRACT(),
            "CALLER_CELL": intToken(0), # KVariable("MSG_SENDER", sort=KSort("Int")),
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
            "GASPRICE_CELL": intToken(0), # KVariable("ORIGIN_ID", sort=KSort("Int")),
            "ORIGIN_CELL": intToken(0),
            "BLOCKHASHES_CELL": list_empty(),
            "CHAINID_CELL": intToken(0),
            "ACCOUNTS_CELL": list_empty(), #KEVM.accounts(init_account_list),
            "PREV_CALLER": KApply(".Account"),
            "PREV_ORIGIN": KApply(".Account"),
            "NEW_CALLER": KApply(".Account"),
            "NEW_ORIGIN": KApply(".Account"),
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
        }

        init_term = Subst(init_subst)(empty_config)
        self.cterm = CTerm.from_kast(init_term)

    def _set_cell(self, cell: str, value: Any, sort: str) -> None:
        self.cterm = CTerm.from_kast(
            set_cell(self.cterm.config, cell, KToken(token=str(value), sort=KSort(name=sort)))
        )