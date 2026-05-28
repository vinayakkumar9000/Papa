# Papa Wallet Orchestration Platform

Papa is a local wallet orchestration platform with backward-compatible legacy tools and an integrated AI routing layer.

## Backward Compatibility

The following legacy commands are preserved:

- `python wallet_gen.py --count 100`
- `python converter.py --format json`
- `python papa.py wallets`

Legacy `wallets` schema remains unchanged:

```sql
CREATE TABLE wallets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  address TEXT NOT NULL UNIQUE,
  private_key TEXT NOT NULL
);
```

## Unified Architecture

- `ai/`: parser, llm boundary, policy router, tool registry, memory, autonomous controller.
- `wallet/`: transaction sender, gas/nonce handling, chains, balances, generator/export wrappers.
- `database/`: manager/migrations compatibility interfaces.
- `cli/`: interactive AI terminal and main CLI package entrypoint.
- `setup/`: bootstrap + install scripts with Ollama and `qwen2.5:3b` provisioning.

## Ollama Integration

Use:

```bash
./setup/install.sh
```

This bootstraps:

- Python virtualenv and dependencies
- Ollama install
- Ollama daemon startup
- `qwen2.5:3b` pull and verification

## Commands

- `python papa.py wallets`
- `python papa.py send --from 1 --to 0x... --amount 1wei --chain skale_base_sepolia`
- `python papa.py balance --wallet 1`
- `python papa.py tx-history`
- `python papa.py networks list`
- `python papa.py doctor`
- `python papa.py ai "generate 20 wallets"`
- `python papa.py ai` (interactive)

## Security + Permissions

- AI is restricted to structured tool calls only.
- Permissions enforce safe vs confirm-required actions.
- Private keys are not printed by CLI tables.
- Destructive shell actions are blocked from AI routing.
