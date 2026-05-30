"""Nonce management helpers with concurrency safety."""

from __future__ import annotations

from threading import Lock
from typing import Dict, Optional

from web3 import Web3


class NonceManager:
    """Thread-safe nonce management with concurrency support.
    
    Maintains local nonce tracking per address to prevent nonce collisions
    in concurrent transaction scenarios.
    """

    # Class-level storage for all nonce managers (singleton per process)
    _instances: Dict[str, "NonceManager"] = {}
    _instances_lock = Lock()

    # Per-address nonce tracking
    _local_nonces: Dict[str, int] = {}
    _nonce_locks: Dict[str, Lock] = {}
    _global_nonce_lock = Lock()

    def __new__(cls) -> "NonceManager":
        """Singleton pattern: return single instance."""
        return super().__new__(cls)

    @classmethod
    def _get_address_lock(cls, address: str) -> Lock:
        """Get or create a lock for a specific address."""
        if address not in cls._nonce_locks:
            with cls._global_nonce_lock:
                if address not in cls._nonce_locks:
                    cls._nonce_locks[address] = Lock()
        return cls._nonce_locks[address]

    @staticmethod
    def next_nonce(w3: Web3, address: str, include_pending: bool = True) -> int:
        """
        Get next usable nonce for a wallet address.
        
        Thread-safe implementation that:
        1. Fetches the chain nonce (pending or latest)
        2. Tracks local pending nonces to prevent collisions
        3. Returns the maximum of chain nonce and local pending nonce
        
        Args:
            w3: Web3 instance
            address: Wallet address
            include_pending: Whether to include pending transactions
            
        Returns:
            Next available nonce
        """
        address_lower = address.lower()
        address_lock = NonceManager._get_address_lock(address_lower)

        with address_lock:
            # Get chain nonce (pending state includes mempool)
            block_param = "pending" if include_pending else "latest"
            chain_nonce = int(w3.eth.get_transaction_count(address_lower, block_identifier=block_param))

            # Get local tracked nonce (accounts for nonces we've allocated)
            local_nonce = NonceManager._local_nonces.get(address_lower, 0)

            # Use the maximum to ensure we don't reuse nonces
            next_nonce = max(chain_nonce, local_nonce)

            # Update local nonce for next call
            NonceManager._local_nonces[address_lower] = next_nonce + 1

            return next_nonce

    @staticmethod
    def reset_nonce(address: str) -> None:
        """
        Reset local nonce tracking for an address.
        
        Call this after a transaction is confirmed or on recovery.
        
        Args:
            address: Wallet address to reset
        """
        address_lower = address.lower()
        address_lock = NonceManager._get_address_lock(address_lower)

        with address_lock:
            if address_lower in NonceManager._local_nonces:
                del NonceManager._local_nonces[address_lower]

    @staticmethod
    def sync_nonce(w3: Web3, address: str) -> int:
        """
        Synchronize local nonce with the chain state.
        
        Use this to recover from failed transactions or nonce gaps.
        
        Args:
            w3: Web3 instance
            address: Wallet address
            
        Returns:
            Synchronized nonce from chain
        """
        address_lower = address.lower()
        address_lock = NonceManager._get_address_lock(address_lower)

        with address_lock:
            # Get the actual pending nonce from chain
            chain_nonce = int(w3.eth.get_transaction_count(address_lower, block_identifier="pending"))
            # Reset to chain state
            NonceManager._local_nonces[address_lower] = chain_nonce
            return chain_nonce

    @staticmethod
    def get_local_nonce(address: str) -> Optional[int]:
        """
        Get the local tracked nonce for an address.
        
        Returns None if no nonce has been allocated yet.
        
        Args:
            address: Wallet address
            
        Returns:
            Local tracked nonce or None
        """
        return NonceManager._local_nonces.get(address.lower())

    @staticmethod
    def clear_all() -> None:
        """
        Clear all local nonce tracking.
        
        Use with caution - should only be called in tests or recovery scenarios.
        """
        with NonceManager._global_nonce_lock:
            NonceManager._local_nonces.clear()
