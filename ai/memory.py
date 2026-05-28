"""In-memory state for interpreted intents and dispatcher outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai.parser import Intent


@dataclass(slots=True)
class Memory:
    intents: list[Intent] = field(default_factory=list)
    outputs: list[Any] = field(default_factory=list)

    def remember_intent(self, intent: Intent) -> None:
        self.intents.append(intent)

    def remember_output(self, output: Any) -> None:
        self.outputs.append(output)
