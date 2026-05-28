"""Wallet export service wrapper around legacy converter."""

from __future__ import annotations

from converter import DatabaseConverter


def export_wallets(fmt: str, db_path: str | None = None) -> str:
    converter = DatabaseConverter(quiet=True)
    databases = converter.find_databases()
    selected = converter.select_database(databases, db_path)
    if selected is None:
        raise ValueError("No database selected")
    if not converter.connect_database(selected) or not converter.validate_database():
        raise ValueError("Database validation failed")
    path = converter.export_wallets(fmt)
    converter.close_connection()
    return str(path)
