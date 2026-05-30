-- Initial schema: wallets, transactions, network_configs, wallet_tags, ai_memory, command_history
-- This migration encapsulates all original tables that were created inline

CREATE TABLE IF NOT EXISTS wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL UNIQUE,
    private_key TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_hash TEXT UNIQUE,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    amount_wei TEXT NOT NULL,
    amount_display TEXT NOT NULL,
    chain TEXT NOT NULL,
    status TEXT NOT NULL,
    gas_used INTEGER,
    gas_price_wei TEXT,
    nonce INTEGER,
    explorer_url TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS network_configs (
    key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    rpc_url TEXT NOT NULL,
    explorer TEXT NOT NULL,
    native_token TEXT NOT NULL,
    decimals INTEGER NOT NULL,
    chain_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wallet_tags (
    wallet_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(wallet_id, tag),
    FOREIGN KEY (wallet_id) REFERENCES wallets(id)
);

CREATE TABLE IF NOT EXISTS ai_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_key TEXT NOT NULL,
    memory_type TEXT NOT NULL DEFAULT 'generic',
    memory_value TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(memory_key, memory_type)
);

CREATE TABLE IF NOT EXISTS command_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,
    parsed_intent TEXT,
    outcome TEXT NOT NULL,
    wallet_ref TEXT,
    chain TEXT,
    export_format TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW IF NOT EXISTS tx_history AS
SELECT
    id,
    tx_hash,
    sender,
    receiver,
    amount_wei,
    amount_display,
    chain,
    status,
    gas_used,
    gas_price_wei,
    nonce,
    explorer_url,
    error_message,
    created_at
FROM transactions;
