"""In-memory state for interpreted intents and dispatcher outputs with optional persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from ai.parser import Intent

if TYPE_CHECKING:
    from wallet.database import DatabaseManager


@dataclass(slots=True)
class Memory:
    intents: list[Intent] = field(default_factory=list)
    outputs: list[Any] = field(default_factory=list)
    db: Optional[DatabaseManager] = field(default=None, repr=False)

    def remember_intent(self, intent: Intent) -> None:
        self.intents.append(intent)
        if self.db is not None:
            self._persist_intent(intent)

    def remember_output(self, output: Any) -> None:
        self.outputs.append(output)
        if self.db is not None:
            self._persist_output(output)

    def load_from_db(self) -> None:
        """Load persisted memory from database on startup."""
        if self.db is None:
            return

        # Load persisted intents
        conn = self.db.engine.begin()
        from sqlalchemy import text

        try:
            # Load all intent records
            rows = conn.execute(
                text(
                    """
                    SELECT memory_key, memory_value FROM ai_memory
                    WHERE memory_type = 'intent'
                    ORDER BY memory_key
                    """
                )
            ).mappings().fetchall()

            for row in rows:
                try:
                    intent_data = json.loads(row["memory_value"])
                    intent = Intent(
                        action=intent_data.get("action"),
                        payload=intent_data.get("payload"),
                    )
                    self.intents.append(intent)
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Skip malformed records
                    pass

            # Load all output records
            rows = conn.execute(
                text(
                    """
                    SELECT memory_key, memory_value FROM ai_memory
                    WHERE memory_type = 'output'
                    ORDER BY memory_key
                    """
                )
            ).mappings().fetchall()

            for row in rows:
                try:
                    output_data = json.loads(row["memory_value"])
                    self.outputs.append(output_data)
                except json.JSONDecodeError:
                    # Skip malformed records
                    pass
        finally:
            conn.close()

    def _persist_intent(self, intent: Intent) -> None:
        """Persist an intent to the database."""
        if self.db is None:
            return

        memory_key = f"intent_{len(self.intents) - 1}"
        memory_value = json.dumps(
            {"action": intent.action, "payload": intent.payload}
        )
        self.db.upsert_ai_memory(memory_key, memory_value, memory_type="intent")

    def _persist_output(self, output: Any) -> None:
        """Persist an output to the database."""
        if self.db is None:
            return

        memory_key = f"output_{len(self.outputs) - 1}"
        try:
            memory_value = json.dumps(output)
        except (TypeError, ValueError):
            # If output is not JSON serializable, convert to string
            memory_value = json.dumps(str(output))
        self.db.upsert_ai_memory(memory_key, memory_value, memory_type="output")
