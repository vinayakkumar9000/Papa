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
        self._initialized = False

    def migrate(self) -> None:
        """Run database migrations and seed network data."""
        if self._initialized:
            return
        
        # Import here to avoid circular imports
        from database.migrations import MigrationManager
        
        manager = MigrationManager(self.db_path)
        manager.run_migrations()
        self._seed_networks_from_file()
        self._initialized = True

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

    def get_wallet_by_tag(self, tag: str) -> WalletRecord:
        """Resolve first wallet associated with a tag."""
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT w.id, w.address, w.private_key
                    FROM wallets w
                    INNER JOIN wallet_tags t ON t.wallet_id = w.id
                    WHERE t.tag = :tag
                    ORDER BY w.id ASC
                    LIMIT 1
                    """
                ),
                {"tag": tag},
            ).mappings().first()
        if not row:
            raise ValueError(f"No wallet found for tag {tag}")
        return WalletRecord(
            id=row["id"],
            address=row["address"],
            private_key=secure_private_key(row["private_key"]),
        )

    def resolve_wallet(self, wallet_ref: str) -> WalletRecord:
        """Resolve wallet references by id, address, or tag:<name>."""
        normalized = wallet_ref.strip()
        if normalized.lower().startswith("tag:"):
            return self.get_wallet_by_tag(normalized.split(":", 1)[1].strip())
        if normalized.isdigit():
            return self.get_wallet_by_id(int(normalized))
        return self.get_wallet_by_address(normalized)

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

    def record_command(
        self,
        prompt: str,
        outcome: str,
        parsed_intent: Optional[str] = None,
        wallet_ref: Optional[str] = None,
        chain: Optional[str] = None,
        export_format: Optional[str] = None,
    ) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO command_history
                    (prompt, parsed_intent, outcome, wallet_ref, chain, export_format)
                    VALUES
                    (:prompt, :parsed_intent, :outcome, :wallet_ref, :chain, :export_format)
                    """
                ),
                {
                    "prompt": prompt,
                    "parsed_intent": parsed_intent,
                    "outcome": outcome,
                    "wallet_ref": wallet_ref,
                    "chain": chain,
                    "export_format": export_format,
                },
            )

    def list_recent_commands(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, prompt, parsed_intent, outcome, wallet_ref, chain, export_format, created_at
                    FROM command_history
                    ORDER BY id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
        return [dict(row) for row in rows]

    def upsert_ai_memory(
        self,
        memory_key: str,
        memory_value: str,
        memory_type: str = "generic",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        metadata_json = json.dumps(metadata) if metadata is not None else None
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO ai_memory
                    (memory_key, memory_type, memory_value, metadata_json, updated_at)
                    VALUES
                    (:memory_key, :memory_type, :memory_value, :metadata_json, CURRENT_TIMESTAMP)
                    ON CONFLICT(memory_key, memory_type) DO UPDATE SET
                        memory_value = excluded.memory_value,
                        metadata_json = excluded.metadata_json,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "memory_key": memory_key,
                    "memory_type": memory_type,
                    "memory_value": memory_value,
                    "metadata_json": metadata_json,
                },
            )

    def get_ai_memory(self, memory_key: str, memory_type: str = "generic") -> Optional[Dict[str, Any]]:
        with self.engine.begin() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT id, memory_key, memory_type, memory_value, metadata_json, created_at, updated_at
                    FROM ai_memory
                    WHERE memory_key = :memory_key AND memory_type = :memory_type
                    """
                ),
                {"memory_key": memory_key, "memory_type": memory_type},
            ).mappings().first()
        if not row:
            return None
        item = dict(row)
        metadata_json = item.get("metadata_json")
        if metadata_json:
            try:
                item["metadata"] = json.loads(metadata_json)
            except JSONDecodeError:
                item["metadata"] = None
        else:
            item["metadata"] = None
        return item

    def get_preferred_chain(self) -> Optional[str]:
        memory = self.get_ai_memory("preferred_chain", "preference")
        return memory["memory_value"] if memory else None

    def set_preferred_chain(self, chain: str) -> None:
        self.upsert_ai_memory("preferred_chain", chain, memory_type="preference")

    def get_preferred_export_format(self) -> Optional[str]:
        memory = self.get_ai_memory("preferred_export_format", "preference")
        return memory["memory_value"] if memory else None

    def set_preferred_export_format(self, export_format: str) -> None:
        self.upsert_ai_memory("preferred_export_format", export_format, memory_type="preference")

    def get_recent_wallet_references(self, limit: int = 10) -> List[str]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT wallet_ref
                    FROM command_history
                    WHERE wallet_ref IS NOT NULL AND trim(wallet_ref) <> ''
                    ORDER BY id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).scalars().all()
        seen = set()
        ordered: List[str] = []
        for ref in rows:
            if ref in seen:
                continue
            seen.add(ref)
            ordered.append(ref)
        return ordered

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

    # Transaction Queue Methods (for transaction retry logic)

    def queue_transaction(
        self,
        tx_hash: str,
        wallet_address: str,
        chain: str,
        status: str = "pending",
        max_retries: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a transaction to the retry queue."""
        metadata_json = json.dumps(metadata) if metadata is not None else None
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT OR IGNORE INTO transaction_queue
                    (tx_hash, wallet_address, chain, status, max_retries, metadata_json)
                    VALUES
                    (:tx_hash, :wallet_address, :chain, :status, :max_retries, :metadata_json)
                    """
                ),
                {
                    "tx_hash": tx_hash,
                    "wallet_address": wallet_address,
                    "chain": chain,
                    "status": status,
                    "max_retries": max_retries,
                    "metadata_json": metadata_json,
                },
            )

    def get_queued_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending transactions from the queue."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, tx_hash, wallet_address, chain, status, retry_count, 
                           max_retries, last_attempt_at, next_retry_at, error_message, 
                           metadata_json, created_at, updated_at
                    FROM transaction_queue
                    WHERE status = 'pending'
                    ORDER BY next_retry_at ASC NULLS FIRST
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
        
        result = []
        for row in rows:
            item = dict(row)
            if item.get("metadata_json"):
                try:
                    item["metadata"] = json.loads(item["metadata_json"])
                except JSONDecodeError:
                    item["metadata"] = None
            else:
                item["metadata"] = None
            result.append(item)
        return result

    def update_queued_transaction(
        self,
        tx_hash: str,
        status: str,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None,
        next_retry_at: Optional[str] = None,
    ) -> None:
        """Update a queued transaction's status and retry information."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE transaction_queue
                    SET status = :status,
                        error_message = :error_message,
                        retry_count = COALESCE(:retry_count, retry_count),
                        next_retry_at = :next_retry_at,
                        last_attempt_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tx_hash = :tx_hash
                    """
                ),
                {
                    "tx_hash": tx_hash,
                    "status": status,
                    "error_message": error_message,
                    "retry_count": retry_count,
                    "next_retry_at": next_retry_at,
                },
            )

    def remove_queued_transaction(self, tx_hash: str) -> None:
        """Remove a transaction from the queue."""
        with self.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM transaction_queue WHERE tx_hash = :tx_hash"),
                {"tx_hash": tx_hash},
            )

    # Balance Cache Methods (for reducing RPC calls)

    def cache_balance(self, wallet_address: str, chain: str, balance_wei: str) -> None:
        """Cache a wallet's balance."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO balance_cache (wallet_address, chain, balance_wei)
                    VALUES (:wallet_address, :chain, :balance_wei)
                    ON CONFLICT(wallet_address, chain) DO UPDATE SET
                        balance_wei = excluded.balance_wei,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "wallet_address": wallet_address,
                    "chain": chain,
                    "balance_wei": balance_wei,
                },
            )

    def get_cached_balance(self, wallet_address: str, chain: str) -> Optional[str]:
        """Get cached balance for a wallet."""
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT balance_wei FROM balance_cache
                    WHERE wallet_address = :wallet_address AND chain = :chain
                    """
                ),
                {"wallet_address": wallet_address, "chain": chain},
            ).scalar()
        return result

    def list_cached_balances(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get cached balances for a wallet across all chains."""
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT wallet_address, chain, balance_wei, updated_at
                    FROM balance_cache
                    WHERE wallet_address = :wallet_address
                    ORDER BY updated_at DESC
                    """
                ),
                {"wallet_address": wallet_address},
            ).mappings().all()
        return [dict(row) for row in rows]

    def clear_expired_balance_cache(self, hours: int = 24) -> int:
        """Clear balance cache entries older than specified hours."""
        with self.engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    DELETE FROM balance_cache
                    WHERE datetime(updated_at) < datetime('now', '-' || :hours || ' hours')
                    """
                ),
                {"hours": hours},
            )
        return result.rowcount if result.rowcount else 0

