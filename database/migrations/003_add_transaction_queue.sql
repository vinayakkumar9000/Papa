-- Transaction queue table for managing pending transactions
-- Enables robust transaction retry logic with exponential backoff

CREATE TABLE IF NOT EXISTS transaction_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_hash TEXT UNIQUE NOT NULL,
    wallet_address TEXT NOT NULL,
    chain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 5,
    last_attempt_at TEXT,
    next_retry_at TEXT,
    error_message TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wallet_address) REFERENCES wallets(address)
);

-- Index for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_transaction_queue_status_retry 
    ON transaction_queue(status, next_retry_at);

CREATE INDEX IF NOT EXISTS idx_transaction_queue_chain_status 
    ON transaction_queue(chain, status);

CREATE INDEX IF NOT EXISTS idx_transaction_queue_wallet_address 
    ON transaction_queue(wallet_address);
