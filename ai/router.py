"""Policy-enforced dispatcher with strict structured tool-call execution."""

from __future__ import annotations

from typing import Any

from ai.parser import intent_to_tool_call, parse_prompt
from ai.permissions import (
    PermissionDecision,
    PermissionError,
    PermissionLevel,
    enforce_tool_permission,
    evaluate_tool_permission,
)
from ai.tools import ToolCall, execute_tool_call, validate_tool_call


class RoutingError(ValueError):
    """Raised when a prompt cannot be safely routed."""


class ConfirmationRequired(PermissionError):
    """Raised when a tool requires user confirmation before execution."""

    def __init__(self, call: ToolCall, decision: PermissionDecision) -> None:
        super().__init__(f"{call.tool}: {decision.reason}")
        self.call = call
        self.decision = decision


def dispatch_tool_call(call: ToolCall, *, confirmed: bool = False) -> Any:
    """Dispatch already-structured calls only; raw shell is intentionally unsupported."""
    decision = evaluate_tool_permission(call.tool, confirmed=confirmed)
    if decision.level == PermissionLevel.CONFIRM_REQUIRED and not confirmed:
        raise ConfirmationRequired(call, decision)
    enforce_tool_permission(call.tool, confirmed=confirmed)
    validate_tool_call(call)
    return execute_tool_call(call)


def route_prompt(prompt: str, *, confirmed: bool = False) -> Any:
    """Interpret a natural-language prompt, then dispatch as a typed tool call."""
    intent = parse_prompt(prompt)
    if intent is None:
        raise RoutingError("No supported intent found in prompt")

    call = intent_to_tool_call(intent)
    try:
        return dispatch_tool_call(call, confirmed=confirmed)
    except ConfirmationRequired:
        raise
    except PermissionError as exc:
        raise RoutingError(str(exc)) from exc
