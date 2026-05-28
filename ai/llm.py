"""LLM interpretation boundary: convert text into normalized intents only."""

from __future__ import annotations

from ai.parser import Intent, parse_prompt


def interpret(prompt: str) -> Intent | None:
    """Interpret user input without performing side effects."""
    return parse_prompt(prompt)
