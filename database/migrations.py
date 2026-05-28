"""Database migration entrypoints for Papa."""

from wallet.database import DatabaseManager


def migrate(db_path: str | None = None) -> None:
    DatabaseManager(db_path=db_path).migrate()
