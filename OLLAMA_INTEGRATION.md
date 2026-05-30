# Ollama LLM Integration

## Overview

Papa AI now uses **Ollama LLM inference** for real prompt interpretation, replacing the previous regex-only parsing. The integration:

- ✅ Preserves the entire existing router architecture
- ✅ Maintains permission checks and security policies
- ✅ Provides graceful fallback to regex parser
- ✅ Uses **qwen2.5:3b** as the default model
- ✅ Loads system.txt, tools.txt, and safety.txt prompts

## Architecture

### Flow: User Prompt → Ollama Inference → Intent → Router → Execution

```
User Input
    ↓
ai/llm.py::interpret()
    ↓
[Try Ollama LLM Inference]
    ↓
[On failure: Fallback to Regex Parser]
    ↓
Intent Object (action + payload)
    ↓
ai/router.py::route_prompt()
    ↓
Permission Check (ai/permissions.py)
    ↓
Tool Execution (ai/tools.py::execute_tool_call)
```

## Implementation Details

### New Module: `ai/ollama_inference.py`

**Functions:**
- `infer_intent_from_llm(prompt, model="qwen2.5:3b")` - Main LLM inference function
- `_load_prompt_file(filename)` - Loads prompt files from ai/prompts/
- `_construct_system_prompt()` - Combines all prompts into unified context
- `_parse_llm_response(response)` - Parses JSON response into Intent

**Features:**
- Loads system.txt, tools.txt, safety.txt automatically
- Constructs JSON-formatted prompt for structured tool calling
- Parses LLM response into `Intent(action, payload)` objects
- Logs all inference results for debugging
- Graceful error handling

### Updated: `ai/llm.py`

Changed from:
```python
def interpret(prompt: str) -> Intent | None:
    return parse_prompt(prompt)  # Regex only
```

To:
```python
def interpret(prompt: str) -> Intent | None:
    # Try LLM inference first
    intent = infer_intent_from_llm(prompt)
    if intent is not None:
        return intent
    
    # Fallback to regex parser
    return parse_prompt(prompt)
```

## Supported Tools

The LLM is instructed on these tools via tools.txt:

1. **generate_wallets** - Create new wallet addresses
2. **send_transaction** - Transfer funds between wallets
3. **export_wallets** - Export wallet data in multiple formats
4. **show_balances** - Check account balances
5. **show_transactions** - Display transaction history

## Prompt Files

### system.txt
Foundation system prompt that defines Papa AI's role and constraints.

### tools.txt
Describes all available tools with their signatures and parameter types.

### safety.txt
Safety rules enforced by the LLM:
- Reject shell execution requests
- Reject unsupported commands
- Enforce allow-listed tools only
- Preserve interpretation/execution separation

## Usage

### When Ollama is Running

```python
from ai.llm import interpret
intent = interpret("generate 5 wallets tagged production")
# Returns: Intent(action='generate_wallets', payload={'count': 5, 'tag': 'production'})
```

The LLM processes the prompt and returns structured tool calls as JSON:
```json
{"tool": "generate_wallets", "args": {"count": 5, "tag": "production"}}
```

### When Ollama is Unavailable

The system automatically falls back to regex parsing:
```
Ollama inference failed: ConnectError: ...
[Fallback to regex parser]
```

## Preserved Components

✅ **No changes** to:
- `ai/router.py` - Router dispatch logic unchanged
- `ai/permissions.py` - Permission policies unchanged
- `ai/tools.py` - Tool registry and validation unchanged
- `ai/parser.py` - Regex parser still available as fallback
- `ai/brain.py` - Brain architecture unchanged
- `ai/autonomous.py` - Autonomous controller unchanged

## Requirements

Already installed (requirements.txt):
- `ollama==0.3.3` - Official Ollama Python client

## Setup

1. Ensure Ollama is installed: `./setup/install.sh`
2. Download model: `ollama pull qwen2.5:3b`
3. Start daemon: `ollama serve`
4. Papa will automatically use LLM inference on next run

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Ollama running | Use LLM inference |
| Ollama unreachable | Fall back to regex, log warning |
| Invalid JSON response | Fall back to regex, log warning |
| Unsupported tool in response | Fall back to regex, log warning |
| Empty LLM response | Fall back to regex, log warning |

## Testing

Run verification:
```bash
python3 << 'EOF'
from ai.llm import interpret
from ai.router import route_prompt

# Test with fallback
prompt = "generate 3 wallets"
intent = interpret(prompt)
print(f"Intent: {intent.action}")

# Test complete flow
result = route_prompt(prompt)
print(f"Result: {result}")
EOF
```

## Performance Notes

- LLM inference adds latency (~1-5 seconds depending on model size)
- Regex fallback is instant (<1ms)
- Both paths preserve all safety guarantees
- Permission checks run after interpretation regardless of path

## Future Enhancements

Possible improvements:
- Add confidence scores to LLM interpretations
- Implement multi-turn conversation support
- Add reasoning/explanation extraction from LLM
- Support for custom model selection
- Response caching for identical prompts
