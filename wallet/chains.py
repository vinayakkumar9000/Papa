"""Network configuration loading and management."""

from __future__ import annotations

from typing import Dict, List

from wallet.database import DatabaseManager
from wallet.models import ChainConfig


class ChainRegistry:
    """Chain registry backed by network_configs table seeded from config/networks.json."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def get(self, key: str) -> ChainConfig:
        for item in self.db.list_networks():
            if item["key"] == key:
                return ChainConfig(**item)
        raise ValueError(f"Unknown chain '{key}'. Use 'papa networks list'.")

    def list(self) -> List[ChainConfig]:
        return [ChainConfig(**item) for item in self.db.list_networks()]

    def add(self, key: str, config: Dict[str, str | int]) -> None:
        self.db.upsert_network(key, config)

    def remove(self, key: str) -> None:
        self.db.deactivate_network(key)
