"""Centralized AI tool registry with typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal

ToolName = Literal[
    "generate_wallets",
    "send_transaction",
    "export_wallets",
    "show_balances",
    "show_transactions",
]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Structured tool-call envelope accepted by the dispatcher."""

    tool: ToolName
    args: Dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Declarative schema + executor binding for a tool."""

    name: ToolName
    schema: Dict[str, type]
    executor: Callable[..., Any]


def _generate_wallets(*, count: int, tag: str | None = None) -> Dict[str, Any]:
    return {"action": "generate_wallets", "count": count, "tag": tag}


def _send_transaction(*, from_wallet: int, to_wallet: int, amount: str) -> Dict[str, Any]:
    return {
        "action": "send_transaction",
        "from_wallet": from_wallet,
        "to_wallet": to_wallet,
        "amount": amount,
    }


def _export_wallets(*, format: str) -> Dict[str, Any]:
    return {"action": "export_wallets", "format": format}


def _show_balances(*, wallet: int | None = None, chain: str | None = None) -> Dict[str, Any]:
    return {"action": "show_balances", "wallet": wallet, "chain": chain}


def _show_transactions(*, limit: int = 20) -> Dict[str, Any]:
    return {"action": "show_transactions", "limit": limit}


TOOL_REGISTRY: Dict[ToolName, ToolSpec] = {
    "generate_wallets": ToolSpec(
        name="generate_wallets",
        schema={"count": int, "tag": (str, type(None))},
        executor=_generate_wallets,
    ),
    "send_transaction": ToolSpec(
        name="send_transaction",
        schema={"from_wallet": int, "to_wallet": int, "amount": str},
        executor=_send_transaction,
    ),
    "export_wallets": ToolSpec(
        name="export_wallets",
        schema={"format": str},
        executor=_export_wallets,
    ),
    "show_balances": ToolSpec(
        name="show_balances",
        schema={"wallet": (int, type(None)), "chain": (str, type(None))},
        executor=_show_balances,
    ),
    "show_transactions": ToolSpec(
        name="show_transactions",
        schema={"limit": int},
        executor=_show_transactions,
    ),
}


def validate_tool_call(call: ToolCall) -> None:
    """Validate tool name and argument types against the registry."""
    spec = TOOL_REGISTRY.get(call.tool)
    if spec is None:
        raise ValueError(f"Unknown tool: {call.tool}")

    for key, expected_type in spec.schema.items():
        if key not in call.args:
            raise ValueError(f"Missing required argument: {key}")
        if not isinstance(call.args[key], expected_type):
            raise TypeError(f"Invalid type for '{key}': expected {expected_type}, got {type(call.args[key])}")

    extra = set(call.args).difference(spec.schema)
    if extra:
        raise ValueError(f"Unexpected arguments for {call.tool}: {sorted(extra)}")


def execute_tool_call(call: ToolCall) -> Any:
    """Execute a validated, structured tool call via the registry."""
    validate_tool_call(call)
    spec = TOOL_REGISTRY[call.tool]
    return spec.executor(**call.args)
