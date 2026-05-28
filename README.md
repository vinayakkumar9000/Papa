# Papa Wallet System

Papa now includes a modular multi-chain wallet orchestration layer while preserving the legacy tools:

- `wallet_gen.py` (existing wallet generation into SQLite)
- `converter.py` (existing wallet export converter)
- `papa.py` (new Typer CLI for tx, balances, networks, and history)

## Backward Compatibility

The original `wallets` table is preserved:

```sql
CREATE TABLE wallets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  address TEXT NOT NULL UNIQUE,
  private_key TEXT NOT NULL
);
```

Legacy commands continue to work:

```bash
python wallet_gen.py --count 1000
python converter.py --format json
```

## New Architecture

```text
config/
  networks.json
  settings.yaml
wallet/
  balance.py
  chains.py
  database.py
  gas.py
  nonce.py
  tx_sender.py
ai/
  parser.py
  router.py
  tools.py
utils/
  validators.py
  formatters.py
  helpers.py
papa.py
install.sh
```

## Database Extensions

Migrations create additional tables safely:

- `transactions`
- `network_configs`
- `wallet_tags`

No existing tables are dropped or altered destructively.

## Install

```bash
chmod +x install.sh
./install.sh
source .venv/bin/activate
```

## CLI Usage

### List wallets

```bash
python papa.py wallets --limit 20
```

### Send transaction

```bash
python papa.py send --from 1 --to 0xABCDEFabcdefABCDEFabcdefABCDEFabcdefABCD --amount 1wei --chain skale_base_sepolia
```

### Check balance

```bash
python papa.py balance --wallet 1 --chain skale_base_sepolia
```

### Show transaction history

```bash
python papa.py tx-history --limit 50
```

### Network management

```bash
python papa.py networks list
python papa.py networks add my_chain "My Chain" https://rpc.example https://explorer.example TOKEN 18 12345
python papa.py networks remove my_chain
```

### Batch send (multi-wallet ready)

```bash
python papa.py batch-send --count 50 --to 0xABCDEFabcdefABCDEFabcdefABCDEFabcdefABCD --amount 1wei --chain skale_base_sepolia
```

## Config

### `config/networks.json`

Network metadata is externalized and unlimited chains can be added.

### `config/settings.yaml`

Contains default chain, DB path, gas strategy, retry policy, and RPC timeout.

## Security Notes

- Private keys are never printed by the new CLI.
- Sensitive key handling is masked and optional encrypted JSON keystore values are supported via `PAPA_WALLET_PASSWORD`.
- Logs are rotated under `logs/` (`tx.log`, `wallet.log`, `errors.log`).

## AI-Ready Placeholders

The `ai/` package provides parser/router scaffolding for future Ollama integration.

Example intent parsing supported:

`send 1 wei from wallet 2 to wallet 8` →
`{"tool":"send_transaction","args":{"from_wallet":2,"to_wallet":8,"amount":"1wei"}}`
