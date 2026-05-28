"""Natural-language parser that normalizes prompts into structured intents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict

from ai.tools import ToolCall


@dataclass(frozen=True, slots=True)
class Intent:
    """Normalized payload used by the router and policy layers."""

    action: str
    payload: Dict[str, Any]


_SEND_RE = re.compile(
    r"send\s+(?P<amount>[0-9.]+\s*(?:wei|gwei|ether))\s+from\s+wallet\s+(?P<from>\d+)\s+to\s+wallet\s+(?P<to>\d+)",
    re.IGNORECASE,
)
_GEN_RE = re.compile(r"(?:generate|create)\s+(?P<count>\d+)\s+wallets?(?:\s+tagged\s+(?P<tag>[\w-]+))?", re.IGNORECASE)
_EXPORT_RE = re.compile(r"export\s+wallets?\s+(?:as|to)\s+(?P<format>json|csv|txt)", re.IGNORECASE)
_BALANCE_RE = re.compile(r"(?:show|check)\s+balances?(?:\s+for\s+wallet\s+(?P<wallet>\d+))?(?:\s+on\s+(?P<chain>[\w-]+))?", re.IGNORECASE)
_TX_RE = re.compile(r"(?:show|list|display)\s+transactions?(?:\s+(?P<limit>\d+))?", re.IGNORECASE)


def parse_prompt(prompt: str) -> Intent | None:
    text = prompt.strip()

    if match := _SEND_RE.search(text):
        return Intent(
            action="send_transaction",
            payload={
                "from_wallet": int(match.group("from")),
                "to_wallet": int(match.group("to")),
                "amount": match.group("amount").replace(" ", ""),
            },
        )

    if match := _GEN_RE.search(text):
        return Intent(action="generate_wallets", payload={"count": int(match.group("count")), "tag": match.group("tag")})

    if match := _EXPORT_RE.search(text):
        return Intent(action="export_wallets", payload={"format": match.group("format").lower()})

    if match := _BALANCE_RE.search(text):
        wallet = int(match.group("wallet")) if match.group("wallet") else None
        chain = match.group("chain").lower() if match.group("chain") else None
        return Intent(action="show_balances", payload={"wallet": wallet, "chain": chain})

    if match := _TX_RE.search(text):
        return Intent(action="show_transactions", payload={"limit": int(match.group("limit")) if match.group("limit") else 20})

    return None


def intent_to_tool_call(intent: Intent) -> ToolCall:
    """Convert normalized intent payload to a structured tool call."""
    return ToolCall(tool=intent.action, args=intent.payload)
