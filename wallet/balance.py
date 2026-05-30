"""Balance checking module for single and multi-wallet operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable, List

from web3 import HTTPProvider, Web3

from utils.formatters import format_native_amount
from utils.helpers import load_settings
from wallet.chains import ChainRegistry
from wallet.database import DatabaseManager
from wallet.rpc_manager import RpcManager


@dataclass(slots=True)
class BalanceResult:
    """Native balance response object."""

    wallet_id: int
    address: str
    chain: str
    balance_wei: int
    formatted: str


class BalanceService:
    """Balance service with sync + async-ready access patterns."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.settings = load_settings()
        self.chain_registry = ChainRegistry(db)
        self._rpc_managers: dict[str, RpcManager] = {}

    def _web3(self, rpc_url: str) -> Web3:
        timeout = int(self.settings.get("rpc_timeout", 20))
        return Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": timeout}))

    def _get_rpc_manager(self, chain_key: str, rpc_url: str) -> RpcManager:
        """Get or create an RPC manager for a chain."""
        if chain_key not in self._rpc_managers:
            rpc_urls = [rpc_url]
            timeout = int(self.settings.get("rpc_timeout", 20))
            self._rpc_managers[chain_key] = RpcManager(rpc_urls, timeout=timeout)
        return self._rpc_managers[chain_key]

    def get_wallet_balance(self, wallet_ref: str, chain_key: str) -> BalanceResult:
        chain = self.chain_registry.get(chain_key)
        wallet = self.db.resolve_wallet(str(wallet_ref))
        w3 = self._web3(chain.rpc_url)

        if not w3.is_connected():
            raise ConnectionError(f"RPC connection failed for {chain.name}")

        wei_value = int(w3.eth.get_balance(wallet.address))
        return BalanceResult(
            wallet_id=wallet.id,
            address=wallet.address,
            chain=chain.key,
            balance_wei=wei_value,
            formatted=format_native_amount(wei_value, chain.decimals, chain.native_token),
        )

    def get_multi_wallet_balances(self, wallet_refs: Iterable[str], chain_key: str) -> List[BalanceResult]:
        return [self.get_wallet_balance(ref, chain_key) for ref in wallet_refs]

    async def get_multi_wallet_balances_async(self, wallet_refs: Iterable[str], chain_key: str) -> List[BalanceResult]:
        """
        Get balances for multiple wallets concurrently using thread pool.
        
        Uses thread pool to avoid blocking on I/O operations.
        """
        tasks = [asyncio.to_thread(self.get_wallet_balance, ref, chain_key) for ref in wallet_refs]
        return list(await asyncio.gather(*tasks))

    async def get_wallet_balance_async(self, wallet_ref: str, chain_key: str) -> BalanceResult:
        """
        Get wallet balance asynchronously using async RPC layer.
        
        Uses async RPC manager for non-blocking RPC calls.
        """
        chain = self.chain_registry.get(chain_key)
        wallet = self.db.resolve_wallet(str(wallet_ref))
        
        # Use async RPC manager
        rpc_manager = self._get_rpc_manager(chain_key, chain.rpc_url)
        w3 = await rpc_manager.get_web3_async()
        
        if not w3.is_connected():
            raise ConnectionError(f"RPC connection failed for {chain.name}")
        
        # Run blocking get_balance in thread pool
        wei_value = await asyncio.to_thread(lambda: int(w3.eth.get_balance(wallet.address)))
        
        return BalanceResult(
            wallet_id=wallet.id,
            address=wallet.address,
            chain=chain.key,
            balance_wei=wei_value,
            formatted=format_native_amount(wei_value, chain.decimals, chain.native_token),
        )

    async def get_multi_wallet_balances_async_native(self, wallet_refs: Iterable[str], chain_key: str) -> List[BalanceResult]:
        """
        Get balances for multiple wallets concurrently using native async RPC layer.
        
        Improved version that uses async RPC manager instead of just thread wrapping.
        """
        tasks = [self.get_wallet_balance_async(ref, chain_key) for ref in wallet_refs]
        return list(await asyncio.gather(*tasks))
