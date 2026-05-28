"""Policy-enforced dispatcher with strict structured tool-call execution."""

from __future__ import annotations

from typing import Any

from ai.parser import intent_to_tool_call, parse_prompt
from ai.permissions import PermissionError, enforce_tool_permission
from ai.tools import ToolCall, execute_tool_call, validate_tool_call


class RoutingError(ValueError):
    """Raised when a prompt cannot be safely routed."""


def dispatch_tool_call(call: ToolCall) -> Any:
    """Dispatch already-structured calls only; raw shell is intentionally unsupported."""
    enforce_tool_permission(call.tool)
    validate_tool_call(call)
    return execute_tool_call(call)


def route_prompt(prompt: str) -> Any:
    """Interpret a natural-language prompt, then dispatch as a typed tool call."""
    intent = parse_prompt(prompt)
    if intent is None:
        raise RoutingError("No supported intent found in prompt")

    call = intent_to_tool_call(intent)
    try:
        return dispatch_tool_call(call)
    except PermissionError as exc:
        raise RoutingError(str(exc)) from exc
