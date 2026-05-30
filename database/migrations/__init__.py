"""Database migration system for Papa."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from utils.helpers import load_settings


class MigrationManager:
    """Manages database schema migrations with version tracking."""

    SCHEMA_VERSION_TABLE = "schema_version"
    MIGRATIONS_DIR = Path(__file__).parent

    def __init__(self, db_path: Optional[str] = None):
        settings = load_settings()
        self.db_path = db_path or str(settings["database_path"])
        self.engine: Engine = create_engine(f"sqlite:///{self.db_path}", future=True)

    def run_migrations(self) -> None:
        """Apply all pending migrations in order."""
        self._ensure_version_table()
        current_version = self._get_current_version()
        migrations = self._get_pending_migrations(current_version)

        for version, migration_path in migrations:
            self._apply_migration(version, migration_path)

    def _ensure_version_table(self) -> None:
        """Create schema_version table if it doesn't exist."""
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.SCHEMA_VERSION_TABLE} (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                    """
                )
            )

    def _get_current_version(self) -> int:
        """Get the current schema version from the database."""
        with self.engine.begin() as conn:
            result = conn.execute(
                text(f"SELECT MAX(version) FROM {self.SCHEMA_VERSION_TABLE}")
            ).scalar()
        return result or 0

    def _get_pending_migrations(self, current_version: int) -> list[tuple[int, Path]]:
        """Get list of pending migrations sorted by version."""
        pending = []
        
        # Find all migration files matching pattern NNN_name.sql
        for migration_file in sorted(self.MIGRATIONS_DIR.glob("*.sql")):
            match = re.match(r"(\d+)_", migration_file.name)
            if not match:
                continue
            
            version = int(match.group(1))
            if version > current_version:
                pending.append((version, migration_file))
        
        return pending

    def _apply_migration(self, version: int, migration_path: Path) -> None:
        """Apply a single migration and update version tracking."""
        sql_content = migration_path.read_text(encoding="utf-8")
        
        with self.engine.begin() as conn:
            # Execute migration SQL (handle multiple statements)
            for statement in self._split_sql_statements(sql_content):
                if statement.strip():
                    conn.execute(text(statement))
            
            # Record migration version
            conn.execute(
                text(
                    f"""
                    INSERT INTO {self.SCHEMA_VERSION_TABLE} (version, description)
                    VALUES (:version, :description)
                    """
                ),
                {"version": version, "description": migration_path.name},
            )

    @staticmethod
    def _split_sql_statements(sql_content: str) -> list[str]:
        """Split SQL content into individual statements."""
        # Remove comments and normalize whitespace
        lines = []
        for line in sql_content.split("\n"):
            # Remove SQL comments
            if "--" in line:
                line = line[: line.index("--")]
            line = line.strip()
            if line:
                lines.append(line)
        
        # Join lines and split by semicolon
        content = " ".join(lines)
        statements = []
        current = []
        
        for char in content:
            if char == ";":
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(char)
        
        # Don't forget last statement if no trailing semicolon
        stmt = "".join(current).strip()
        if stmt:
            statements.append(stmt)
        
        return statements


def migrate(db_path: str | None = None) -> None:
    """Entrypoint for database migrations."""
    manager = MigrationManager(db_path=db_path)
    manager.run_migrations()


__all__ = ["MigrationManager", "migrate"]

