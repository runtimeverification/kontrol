from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from web3 import Web3

if TYPE_CHECKING:
    from typing import Final

_LOGGER: Final = logging.getLogger(__name__)


class Web3Providers:
    """
    A simple registry that returns a single Web3 instance per unique URL to avoid duplicate sessions and redundant
    connections.
    """

    _instances: dict[str, Web3] = {}

    @classmethod
    def get_provider(cls, url: str) -> Web3:
        if url not in cls._instances:
            _LOGGER.info(f'Creating connection to web3 provider: {url}')
            cls._instances[url] = Web3(Web3.HTTPProvider(url))
        else:
            _LOGGER.debug(f'Reusing existing provider for: {url}')
        return cls._instances[url]


def get_block_metadata(w3: Web3) -> dict[str, int]:
    block_number = w3.eth.block_number
    w3.eth.chain_id
    block_metadata = w3.eth.get_block(block_number)
    # TODO: fetch rest of the block header
    # TODO: fix error: Dict entry 3 has incompatible type "str": "object"; expected "str": "int"  [dict-item]

    return {
        'block_number': block_number,
        'chain_id': w3.eth.chain_id,
        'gas_limit': block_metadata.get('gasLimit', 9223372036854775807),
        'gas_price': int(str(block_metadata.get('gasPrice', 0))),
        'block_base_fee_per_gas': block_metadata.get('baseFeePerGas', 0),
        'block_coinbase': int(block_metadata.get('miner', '0x0'), 0),
        'block_timestamp': block_metadata.get('timestamp', 1),
        'block_difficulty': block_metadata.get('difficulty', 0),
    }
