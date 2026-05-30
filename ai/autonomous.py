"""Autonomous controller wiring memory, interpretation, and execution layers."""

from __future__ import annotations

from typing import Any

from ai.brain import think_and_act
from ai.llm import interpret
from ai.memory import Memory
from ai.router import dispatch_tool_call
from ai.tools import ToolCall


class AutonomousController:
    def __init__(self) -> None:
        self.memory = Memory()

    def run(self, prompt: str) -> Any:
        intent = interpret(prompt)
        if intent is None:
            raise ValueError("No actionable intent detected")
        self.memory.remember_intent(intent)
        output = think_and_act(prompt)
        self.memory.remember_output(output)
        return output

    def run_confirmed(self, call: ToolCall) -> Any:
        output = dispatch_tool_call(call, confirmed=True)
        self.memory.remember_output(output)
        return output
