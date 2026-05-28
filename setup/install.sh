#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOOTSTRAP="$ROOT_DIR/setup/bootstrap.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required to bootstrap Ollama" >&2
  exit 1
fi

python3 "$BOOTSTRAP"
