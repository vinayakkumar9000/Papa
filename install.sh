#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

python - <<'PY'
from utils.dependency_checks import validate_dependencies

errors = validate_dependencies()
if errors:
    raise SystemExit("Dependency validation failed after install:\n" + "\n".join(f"- {e}" for e in errors))

print("Dependency validation passed")
PY

mkdir -p logs exports config

if [ ! -f config/networks.json ]; then
  cat > config/networks.json <<'JSON'
{
  "skale_base_sepolia": {
    "name": "SKALE Base Sepolia",
    "rpc_url": "https://base-sepolia-testnet.skalenodes.com/v1/jubilant-horrible-ancha",
    "explorer": "https://base-sepolia-testnet-explorer.skalenodes.com",
    "native_token": "CREDIT",
    "decimals": 18,
    "chain_id": 324705682
  }
}
JSON
fi

if [ ! -f config/settings.yaml ]; then
  cat > config/settings.yaml <<'YAML'
default_chain: skale_base_sepolia
database_path: wallets.db
rpc_timeout: 20
retry_count: 3
retry_backoff_seconds: 1.5
gas:
  strategy: auto
  default_limit: 21000
YAML
fi

python - <<'PY'
from wallet.database import DatabaseManager
DatabaseManager().migrate()
print("Database initialized")
PY

echo "Installation complete. Activate with: source .venv/bin/activate"
