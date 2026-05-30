"""LLM interpretation boundary: convert text into normalized intents only."""

from __future__ import annotations

import logging

from ai.ollama_inference import infer_intent_from_llm
from ai.parser import Intent, parse_prompt

logger = logging.getLogger(__name__)


def interpret(prompt: str) -> Intent | None:
    """
    Interpret user input using Ollama LLM with fallback to regex parsing.
    
    Flow:
    1. Try Ollama LLM inference with system + tools + safety prompts
    2. Fall back to regex parser if LLM inference fails or returns None
    """
    # Try LLM-based inference first
    intent = infer_intent_from_llm(prompt)
    
    if intent is not None:
        return intent
    
    # Fallback to regex parser for robustness
    logger.debug(f"Ollama inference returned None, falling back to regex parser")
    return parse_prompt(prompt)
