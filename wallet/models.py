"""Dataclasses for wallet orchestration entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class WalletRecord:
    """Wallet model loaded from the legacy wallets table."""

    id: int
    address: str
    private_key: str


@dataclass(slots=True)
class ChainConfig:
    """Chain/network configuration model."""

    key: str
    name: str
    rpc_url: str
    explorer: str
    native_token: str
    decimals: int
    chain_id: int


@dataclass(slots=True)
class TransactionRecord:
    """Transaction history model for database persistence."""

    tx_hash: str
    sender: str
    receiver: str
    amount_wei: int
    amount_display: str
    chain: str
    status: str
    gas_used: Optional[int] = None
    gas_price_wei: Optional[int] = None
    nonce: Optional[int] = None
    explorer_url: Optional[str] = None
    error_message: Optional[str] = None
