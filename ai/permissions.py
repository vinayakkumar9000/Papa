"""Tool-level permission policy for autonomous dispatch."""

from __future__ import annotations

from ai.tools import ToolName


class PermissionError(Exception):
    """Raised when a tool call is blocked by policy."""


ALLOWED_TOOLS: set[ToolName] = {
    "generate_wallets",
    "send_transaction",
    "export_wallets",
    "show_balances",
    "show_transactions",
}


def enforce_tool_permission(tool: ToolName) -> None:
    """Deny anything outside explicit allow-list."""
    if tool not in ALLOWED_TOOLS:
        raise PermissionError(f"Tool not allowed by policy: {tool}")
