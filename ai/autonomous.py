"""Autonomous controller wiring memory, interpretation, and execution layers."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Optional

from ai.brain import think_and_act
from ai.llm import interpret
from ai.memory import Memory
from ai.router import dispatch_tool_call
from ai.tools import ToolCall

if TYPE_CHECKING:
    from wallet.database import DatabaseManager


class AutonomousController:
    def __init__(self, db: Optional[DatabaseManager] = None) -> None:
        self.memory = Memory(db=db)
        # Load persisted memory from database on startup
        if db is not None:
            self.memory.load_from_db()

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

    async def run_async(self, prompt: str) -> Any:
        """
        Execute autonomous control flow asynchronously.
        
        Interprets user prompt and executes the resulting intent in a non-blocking manner.
        Uses async inference where available with fallback to sync operations.
        
        Args:
            prompt: User input string
            
        Returns:
            Output from executed tool/action
            
        Raises:
            ValueError: If no actionable intent is detected
        """
        # Try async interpretation first, falls back to sync internally
        from ai.ollama_inference import infer_intent_from_llm_async
        
        intent = await infer_intent_from_llm_async(prompt)
        
        if intent is None:
            # Fall back to sync interpret if async inference fails
            intent = interpret(prompt)
        
        if intent is None:
            raise ValueError("No actionable intent detected")
        
        self.memory.remember_intent(intent)
        
        # Dispatch in thread pool to avoid blocking
        output = await asyncio.to_thread(think_and_act, prompt)
        self.memory.remember_output(output)
        
        return output

    async def run_confirmed_async(self, call: ToolCall) -> Any:
        """
        Execute a confirmed tool call asynchronously.
        
        Args:
            call: ToolCall object representing the confirmed action
            
        Returns:
            Output from executed tool
        """
        # Dispatch in thread pool to avoid blocking
        output = await asyncio.to_thread(dispatch_tool_call, call, True)
        self.memory.remember_output(output)
        return output
