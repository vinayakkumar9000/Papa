"""Safe SQLite + SQLAlchemy integration for wallet orchestration."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from utils.helpers import load_settings, project_root, secure_private_key, setup_rotating_logger
from wallet.models import TransactionRecord, WalletRecord


class DatabaseManager:
    """Database manager preserving existing wallets schema and extending metadata."""

    def __init__(self, db_path: Optional[str] = None):
        settings = load_settings()
        self.db_path = db_path or str(settings["database_path"])
        self.engine: Engine = create_engine(f"sqlite:///{self.db_path}", future=True)
        self.logger = setup_rotating_logger("wallet_db", "wallet.log")

    def migrate(self) -> None:
        """Create required extension tables without modifying legacy wallets table."""
        stmts = [
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_hash TEXT UNIQUE,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                amount_wei TEXT NOT NULL,
                amount_display TEXT NOT NULL,
                chain TEXT NOT NULL,
                status TEXT NOT NULL,
                gas_used INTEGER,
                gas_price_wei TEXT,
                nonce INTEGER,
                explorer_url TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS network_configs (
                key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                rpc_url TEXT NOT NULL,
                explorer TEXT NOT NULL,
                native_token TEXT NOT NULL,
                decimals INTEGER NOT NULL,
                chain_id INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS wallet_tags (
                wallet_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wallet_id, tag),
                FOREIGN KEY (wallet_id) REFERENCES wallets(id)
            )
            """,
        ]

        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS wallets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        address TEXT NOT NULL UNIQUE,
                        private_key TEXT NOT NULL
                    )
                    """
                )
            )
            for stmt in stmts:
                conn.execute(text(stmt))

        self._seed_networks_from_file()

    def _seed_networks_from_file(self) -> None:
        networks_path = project_root() / "config" / "networks.json"
        if not networks_path.exists():
            return

        try:
            data: Dict[str, Dict[str, Any]] = json.loads(networks_path.read_text(encoding="utf-8"))
        except JSONDecodeError as exc:
            raise ValueError(f"Invalid network config JSON in {networks_path}") from exc
        with self.engine.begin() as conn:
            for key, cfg in data.items():
                conn.execute(
                    text(
                        """
                        INSERT OR IGNORE INTO network_configs
                        (key, name, rpc_url, explorer, native_token, decimals, chain_id, is_active)
                        VALUES (:key, :name, :rpc_url, :explorer, :native_token, :decimals, :chain_id, 1)
                        """
                    ),
                    {
                        "key": key,
                        "name": cfg["name"],
                        "rpc_url": cfg["rpc_url"],
                        "explorer": cfg["explorer"],
                        "native_token": cfg["native_token"],
                        "decimals": int(cfg["decimals"]),
                        "chain_id": int(cfg["chain_id"]),
                    },
                )

    def get_wallet_by_id(self, wallet_id: int) -> WalletRecord:
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT id, address, private_key FROM wallets WHERE id = :id"),
                {"id": wallet_id},
            ).mappings().first()
        if not row:
            raise ValueError(f"Wallet id {wallet_id} not found")
        return WalletRecord(
            id=row["id"],
            address=row["address"],
            private_key=secure_private_key(row["private_key"]),
        )

    def get_wallet_by_address(self, address: str) -> WalletRecord:
        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT id, address, private_key FROM wallets WHERE lower(address) = lower(:address)"),
                {"address": address},
            ).mappings().first()
        if not row:
            raise ValueError(f"Wallet address {address} not found")
        return WalletRecord(
            id=row["id"],
            address=row["address"],
            private_key=secure_private_key(row["private_key"]),
        )

    def resolve_wallet(self, wallet_ref: str) -> WalletRecord:
        if wallet_ref.isdigit():
            return self.get_wallet_by_id(int(wallet_ref))
        return self.get_wallet_by_address(wallet_ref)

    def list_wallets(self, limit: int = 50, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT w.id, w.address FROM wallets w"
        params: Dict[str, Any] = {"limit": limit}

        if tag:
            query += " INNER JOIN wallet_tags t ON t.wallet_id = w.id WHERE t.tag = :tag"
            params["tag"] = tag

        query += " ORDER BY w.id ASC LIMIT :limit"
        with self.engine.begin() as conn:
            rows = conn.execute(text(query), params).mappings().all()
        return [dict(row) for row in rows]

    def add_wallet_tag(self, wallet_id: int, tag: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT OR IGNORE INTO wallet_tags (wallet_id, tag) VALUES (:wallet_id, :tag)"),
                {"wallet_id": wallet_id, "tag": tag},
            )

    def list_networks(self) -> List[Dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT key, name, rpc_url, explorer, native_token, decimals, chain_id
                    FROM network_configs
                    WHERE is_active = 1
                    ORDER BY key ASC
                    """
                )
            ).mappings().all()
        return [dict(row) for row in rows]

    def upsert_network(self, key: str, config: Dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO network_configs
                    (key, name, rpc_url, explorer, native_token, decimals, chain_id, is_active, updated_at)
                    VALUES (:key, :name, :rpc_url, :explorer, :native_token, :decimals, :chain_id, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        name = excluded.name,
                        rpc_url = excluded.rpc_url,
                        explorer = excluded.explorer,
                        native_token = excluded.native_token,
                        decimals = excluded.decimals,
                        chain_id = excluded.chain_id,
                        is_active = 1,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "key": key,
                    "name": config["name"],
                    "rpc_url": config["rpc_url"],
                    "explorer": config["explorer"],
                    "native_token": config["native_token"],
                    "decimals": int(config["decimals"]),
                    "chain_id": int(config["chain_id"]),
                },
            )

    def deactivate_network(self, key: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE network_configs SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE key = :key"),
                {"key": key},
            )

    def add_transaction(self, tx: TransactionRecord) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO transactions
                    (tx_hash, sender, receiver, amount_wei, amount_display, chain, status, gas_used,
                     gas_price_wei, nonce, explorer_url, error_message)
                    VALUES
                    (:tx_hash, :sender, :receiver, :amount_wei, :amount_display, :chain, :status, :gas_used,
                     :gas_price_wei, :nonce, :explorer_url, :error_message)
                    """
                ),
                {
                    "tx_hash": tx.tx_hash,
                    "sender": tx.sender,
                    "receiver": tx.receiver,
                    "amount_wei": str(tx.amount_wei),
                    "amount_display": tx.amount_display,
                    "chain": tx.chain,
                    "status": tx.status,
                    "gas_used": tx.gas_used,
                    "gas_price_wei": str(tx.gas_price_wei) if tx.gas_price_wei is not None else None,
                    "nonce": tx.nonce,
                    "explorer_url": tx.explorer_url,
                    "error_message": tx.error_message,
                },
            )

    def list_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT tx_hash, sender, receiver, amount_display, chain, status,
                           gas_used, nonce, explorer_url, created_at
                    FROM transactions
                    ORDER BY id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
        return [dict(row) for row in rows]
