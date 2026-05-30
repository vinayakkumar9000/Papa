-- Add strategic indexes for query optimization
-- Improves performance for common access patterns

-- Transactions table indexes
CREATE INDEX IF NOT EXISTS idx_transactions_sender_created 
    ON transactions(sender, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_receiver_created 
    ON transactions(receiver, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_chain_status 
    ON transactions(chain, status);

CREATE INDEX IF NOT EXISTS idx_transactions_tx_hash 
    ON transactions(tx_hash);

-- Wallet tags indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_wallet_tags_wallet_id 
    ON wallet_tags(wallet_id);

CREATE INDEX IF NOT EXISTS idx_wallet_tags_tag 
    ON wallet_tags(tag);

-- AI memory indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_ai_memory_key_type 
    ON ai_memory(memory_key, memory_type);

-- Command history indexes for recent queries
CREATE INDEX IF NOT EXISTS idx_command_history_created 
    ON command_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_command_history_wallet_ref 
    ON command_history(wallet_ref);

-- Network configs index
CREATE INDEX IF NOT EXISTS idx_network_configs_active 
    ON network_configs(is_active);
