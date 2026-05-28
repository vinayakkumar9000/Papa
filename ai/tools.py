"""AI tool catalog placeholders for future Ollama integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(slots=True)
class ToolCall:
    """Standard AI-routed tool call payload."""

    tool: str
    args: Dict[str, Any]


def send_transaction_tool(from_wallet: int, to_wallet: int, amount: str) -> ToolCall:
    """Return normalized transaction call payload."""
    return ToolCall(
        tool="send_transaction",
        args={"from_wallet": from_wallet, "to_wallet": to_wallet, "amount": amount},
    )
