"""Decision boundary between interpretation (LLM) and execution dispatcher."""

from __future__ import annotations

from typing import Any

from ai.llm import interpret
from ai.parser import intent_to_tool_call
from ai.router import dispatch_tool_call


def think_and_act(prompt: str) -> Any:
    """Interpret first, execute second, with strict separation."""
    intent = interpret(prompt)
    if intent is None:
        raise ValueError("Unable to interpret prompt into a known intent")
    return dispatch_tool_call(intent_to_tool_call(intent))
