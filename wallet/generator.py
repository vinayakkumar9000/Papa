"""Wallet generation service wrapper around legacy generator."""

from __future__ import annotations

from wallet_gen import WalletGenerator


def generate_wallets(count: int, db_path: str = "wallets.db", batch_size: int = 1000) -> int:
    generator = WalletGenerator(db_path=db_path)
    return generator.generate_wallets(count=count, batch_size=batch_size)
