"""Ollama-powered LLM inference for structured tool calling."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import aiohttp
import ollama

from ai.parser import Intent, ToolCall

logger = logging.getLogger(__name__)

# Default model configuration
DEFAULT_MODEL = "qwen2.5:3b"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"


def _load_prompt_file(filename: str) -> str:
    """Load prompt file from ai/prompts directory."""
    prompt_path = Path(__file__).parent / "prompts" / filename
    if not prompt_path.exists():
        logger.warning(f"Prompt file not found: {filename}")
        return ""
    return prompt_path.read_text().strip()


def _construct_system_prompt() -> str:
    """Construct the system prompt from all available context files."""
    system_txt = _load_prompt_file("system.txt")
    tools_txt = _load_prompt_file("tools.txt")
    safety_txt = _load_prompt_file("safety.txt")
    
    parts = [
        system_txt,
        "\n",
        tools_txt,
        "\n",
        safety_txt,
        "\n\n",
        "IMPORTANT: Respond ONLY with a valid JSON object. No explanations, no markdown, just JSON.",
        "Response format: {\"tool\": \"tool_name\", \"args\": {\"key\": value, ...}}",
    ]
    
    return "".join(p for p in parts if p)


def _parse_llm_response(response: str) -> Intent | None:
    """Parse LLM response into an Intent object."""
    response = response.strip()
    
    # Try to extract JSON if wrapped in other text
    try:
        # First try direct JSON parsing
        data = json.loads(response)
    except json.JSONDecodeError:
        # Try to find JSON object in the response
        start_idx = response.find("{")
        end_idx = response.rfind("}") + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            try:
                data = json.loads(response[start_idx:end_idx])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response: {response}")
                return None
        else:
            logger.warning(f"No JSON found in response: {response}")
            return None
    
    # Validate required fields
    if not isinstance(data, dict):
        logger.warning(f"Response is not a dict: {type(data)}")
        return None
    
    tool = data.get("tool")
    args = data.get("args", {})
    
    if not tool:
        logger.warning("Response missing 'tool' field")
        return None
    
    if not isinstance(args, dict):
        logger.warning(f"'args' must be a dict, got {type(args)}")
        return None
    
    return Intent(action=tool, payload=args)


def infer_intent_from_llm(prompt: str, model: str = DEFAULT_MODEL) -> Intent | None:
    """
    Use Ollama LLM to interpret a user prompt into a structured Intent.
    
    Args:
        prompt: User input string
        model: Ollama model name (default: qwen2.5:3b)
    
    Returns:
        Intent object if inference succeeds, None otherwise
    """
    try:
        system_prompt = _construct_system_prompt()
        
        # Call Ollama API
        response = ollama.generate(
            model=model,
            prompt=f"{system_prompt}\n\nUser: {prompt}",
            stream=False,
        )
        
        # Extract response text
        response_text = response.get("response", "").strip()
        
        if not response_text:
            logger.warning("Empty response from LLM")
            return None
        
        # Parse into Intent
        intent = _parse_llm_response(response_text)
        
        if intent:
            logger.debug(f"LLM interpreted '{prompt}' -> action={intent.action}, payload={intent.payload}")
        else:
            logger.warning(f"Failed to parse LLM response into Intent")
        
        return intent
    
    except Exception as e:
        logger.error(f"Ollama inference failed: {type(e).__name__}: {e}")
        return None


async def infer_intent_from_llm_async(prompt: str, model: str = DEFAULT_MODEL, base_url: str = OLLAMA_BASE_URL) -> Intent | None:
    """
    Use Ollama LLM to interpret a user prompt into a structured Intent asynchronously.
    
    Falls back to sync version if async HTTP unavailable.
    
    Args:
        prompt: User input string
        model: Ollama model name (default: qwen2.5:3b)
        base_url: Ollama server base URL
    
    Returns:
        Intent object if inference succeeds, None otherwise
    """
    try:
        system_prompt = _construct_system_prompt()
        
        # Try async HTTP call to Ollama API
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            try:
                payload = {
                    "model": model,
                    "prompt": f"{system_prompt}\n\nUser: {prompt}",
                    "stream": False,
                }
                
                async with session.post(f"{base_url}/api/generate", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response_text = data.get("response", "").strip()
                        
                        if not response_text:
                            logger.warning("Empty response from async LLM")
                            return None
                        
                        # Parse into Intent
                        intent = _parse_llm_response(response_text)
                        
                        if intent:
                            logger.debug(f"Async LLM interpreted '{prompt}' -> action={intent.action}, payload={intent.payload}")
                        else:
                            logger.warning(f"Failed to parse async LLM response into Intent")
                        
                        return intent
                    else:
                        logger.warning(f"Ollama async API returned status {resp.status}")
                        return None
            except asyncio.TimeoutError:
                logger.warning("Ollama async inference timed out, falling back to sync")
                # Fall back to sync version
                return infer_intent_from_llm(prompt, model)
            except Exception as e:
                logger.warning(f"Ollama async inference failed: {type(e).__name__}: {e}, falling back to sync")
                # Fall back to sync version
                return infer_intent_from_llm(prompt, model)
    
    except Exception as e:
        logger.error(f"Ollama async inference failed: {type(e).__name__}: {e}")
        return None