-- Balance cache table for reducing RPC calls
-- Improves performance by caching recently queried balances

CREATE TABLE IF NOT EXISTS balance_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT NOT NULL,
    chain TEXT NOT NULL,
    balance_wei TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(wallet_address, chain),
    FOREIGN KEY (wallet_address) REFERENCES wallets(address)
);

-- Index for efficient cache lookups
CREATE INDEX IF NOT EXISTS idx_balance_cache_wallet_chain 
    ON balance_cache(wallet_address, chain);

CREATE INDEX IF NOT EXISTS idx_balance_cache_updated 
    ON balance_cache(updated_at DESC);
