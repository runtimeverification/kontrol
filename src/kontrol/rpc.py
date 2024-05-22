
from typing import TYPE_CHECKING
import logging
import pprint

from typing import Any
from pyk.kast.manip import set_cell
from pyk.cterm import CTerm
from pyk.ktool.krun import KRun
from pyk.rpc.rpc import JsonRpcServer, ServeRpcOptions
from pyk.kast.inner import KSort, KApply, KToken, KSequence

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

        self.krun = KRun(options.definition_dir)
        self.cterm = CTerm.from_kast(self.krun.definition.init_config(KSort('GeneratedTopCell')))

        self._set_default_values()

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


    def exec_add_account(self) -> int:
        # x = self.cterm.cell('X_CELL')
        # y = self.cterm.cell('Y_CELL')
        # self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'K_CELL', KApply('_+Int_', [x, y])))
        
        # self.cterm = CTerm.from_kast(set_cell(self.cterm.config, 'RPC-REQUEST_CELL', KApply('#kontrol_addAccount', [])))
        # pattern = self.krun.kast_to_kore(self.cterm.config, sort=KSort('GeneratedTopCell'))
        # output_kore = self.krun.run_pattern(pattern)
        # self.cterm = CTerm.from_kast(self.krun.kore_to_kast(output_kore))

        rpc_response_cell = self.cterm.cell('RPCRESPONSE_CELL')
        _PPRINT.pprint(rpc_response_cell)
        return 0


    # _PPRINT.pprint(cell)
    def _set_default_values(self) -> None:
        self._set_cell("CHAINID_CELL", 1, 'Int')

    def _set_cell(self, cell: str, value: Any, sort: str) -> None:
        self.cterm = CTerm.from_kast(
            set_cell(self.cterm.config, cell, KToken(token=str(value), sort=KSort(name=sort)))
        )