"""Granular tool permission model for AI orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai.tools import ToolName


class PermissionLevel(str, Enum):
    SAFE = "safe"
    CONFIRM_REQUIRED = "confirm_required"
    BLOCKED = "blocked"


class PermissionError(Exception):
    """Raised when a tool call violates policy."""


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    tool: str
    level: PermissionLevel
    allowed: bool
    reason: str


POLICY: dict[ToolName, PermissionLevel] = {
    "show_balances": PermissionLevel.SAFE,
    "show_transactions": PermissionLevel.SAFE,
    "generate_wallets": PermissionLevel.CONFIRM_REQUIRED,
    "send_transaction": PermissionLevel.CONFIRM_REQUIRED,
    "export_wallets": PermissionLevel.CONFIRM_REQUIRED,
}


def evaluate_tool_permission(tool: ToolName, confirmed: bool = False) -> PermissionDecision:
    level = POLICY.get(tool, PermissionLevel.BLOCKED)
    if level == PermissionLevel.BLOCKED:
        return PermissionDecision(tool, level, False, "blocked by policy")
    if level == PermissionLevel.CONFIRM_REQUIRED and not confirmed:
        return PermissionDecision(tool, level, False, "user confirmation required")
    return PermissionDecision(tool, level, True, "allowed")


def enforce_tool_permission(tool: ToolName, confirmed: bool = False) -> None:
    decision = evaluate_tool_permission(tool, confirmed=confirmed)
    if not decision.allowed:
        raise PermissionError(f"{tool}: {decision.reason}")
