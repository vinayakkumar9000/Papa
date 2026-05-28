"""Prompt parser placeholder for AI command extraction."""

from __future__ import annotations

import re
from typing import Optional

from ai.tools import ToolCall, send_transaction_tool

_SEND_RE = re.compile(
    r"send\s+(?P<amount>[0-9.]+\s*(?:wei|gwei|ether)?)\s+from\s+wallet\s+(?P<from>\d+)\s+to\s+wallet\s+(?P<to>\d+)",
    re.IGNORECASE,
)


def parse_prompt(prompt: str) -> Optional[ToolCall]:
    """Parse simple send prompt into a structured tool call."""
    match = _SEND_RE.search(prompt)
    if not match:
        return None

    return send_transaction_tool(
        from_wallet=int(match.group("from")),
        to_wallet=int(match.group("to")),
        amount=match.group("amount").replace(" ", ""),
    )
