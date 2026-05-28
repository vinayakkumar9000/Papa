"""AI router placeholder for future execution orchestration."""

from __future__ import annotations

from typing import Optional

from ai.parser import parse_prompt
from ai.tools import ToolCall


def route_prompt(prompt: str) -> Optional[ToolCall]:
    """Return parsed tool call for future AI engine routing."""
    return parse_prompt(prompt)
