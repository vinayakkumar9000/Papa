"""Nonce management helpers."""

from __future__ import annotations

from web3 import Web3


class NonceManager:
    """Nonce fetcher for pending/latest state."""

    @staticmethod
    def next_nonce(w3: Web3, address: str, include_pending: bool = True) -> int:
        """Get next usable nonce for a wallet address."""
        block_param = "pending" if include_pending else "latest"
        return int(w3.eth.get_transaction_count(address, block_identifier=block_param))
