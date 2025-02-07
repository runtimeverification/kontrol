from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from kevm_pyk.kevm import KEVM
from pyk.prelude.collections import map_empty
from pyk.prelude.utils import token
from web3 import Web3

if TYPE_CHECKING:
    from typing import Final

    from eth_typing.evm import ChecksumAddress
    from pyk.kast.inner import KApply, KToken

_LOGGER: Final = logging.getLogger(__name__)


class Web3Providers:
    """A simple registry that returns a single Web3 instance per unique URL to avoid duplicate sessions and redundant
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

    @staticmethod
    def get_checksum_address(address_token: KToken) -> ChecksumAddress:
        """Converts a KToken representing an address into a checksum address string."""
        hex_address = Web3.to_hex(int(address_token.token))
        return Web3.to_checksum_address(hex_address)


def get_block_metadata(provider: Web3) -> dict[str, int]:
    block_number = provider.eth.block_number
    block_metadata = provider.eth.get_block(block_number)
    # TODO: fetch rest of the block header

    return {
        'block_number': block_number,
        'chain_id': provider.eth.chain_id,
        'gas_limit': block_metadata.get('gasLimit', 9223372036854775807),
        'gas_price': int(str(block_metadata.get('gasPrice', 0))),
        'block_base_fee_per_gas': block_metadata.get('baseFeePerGas', 0),
        'block_coinbase': int(block_metadata.get('miner', '0x0'), 0),
        'block_timestamp': block_metadata.get('timestamp', 1),
        'block_difficulty': block_metadata.get('difficulty', 0),
    }


def fetch_account_from_provider(provider: Web3, target_address: KToken) -> tuple[KToken, KToken, KApply]:
    """Fetch the account's code and balance from the provider, and return a tuple containing:
    - A KToken representing the account code.
    - A KApply account cell with the fetched data and empty storage.
    """

    code_token = fetch_code_from_provider(provider, target_address)
    balance_token = fetch_balance_from_provider(provider, target_address)

    return (
        code_token,
        balance_token,
        KEVM.account_cell(
            id=target_address,
            balance=balance_token,
            code=code_token,
            storage=map_empty(),
            orig_storage=map_empty(),
            transient_storage=map_empty(),
            nonce=token(0),
        ),
    )


def fetch_storage_value_from_provider(provider: Web3, target_address: KToken, target_slot: KToken) -> KToken:
    """Fetch the value stored at a specific slot for a given account address from the provider,
    and return it as a KToken.
    """
    checksum_addr = Web3Providers.get_checksum_address(target_address)
    slot = int(target_slot.token)
    _LOGGER.info(f'Reading storage slot {slot} from {checksum_addr}')

    try:
        storage_bytes = provider.eth.get_storage_at(checksum_addr, slot)
    except Exception as e:
        _LOGGER.error(f'Error fetching storage at slot {slot} for {checksum_addr}: {e}')
        raise

    value = int.from_bytes(storage_bytes, byteorder='big')
    return token(value)


def fetch_code_from_provider(provider: Web3, target_address: KToken) -> KToken:
    """Fetch the code of a given account address from the provider and return it as a KToken."""

    checksum_addr = Web3Providers.get_checksum_address(target_address)
    _LOGGER.info(f'Reading code for {checksum_addr}')

    try:
        code_bytes = provider.eth.get_code(checksum_addr)
    except Exception as e:
        _LOGGER.error(f'Error fetching code for {checksum_addr}: {e}')
        raise
    return token(bytes(code_bytes))


def fetch_balance_from_provider(provider: Web3, target_address: KToken) -> KToken:
    """Fetch the balance of a given account address from the provider and return it as a KToken."""

    checksum_addr = Web3Providers.get_checksum_address(target_address)
    _LOGGER.info(f'Reading balance for {checksum_addr}')

    try:
        balance = provider.eth.get_balance(checksum_addr)
    except Exception as e:
        _LOGGER.error(f'Error fetching balance for {checksum_addr}: {e}')
        raise
    return token(balance)
