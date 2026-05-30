# Papa Database Architecture

## Overview

Papa uses a migration-based database schema management system that supports SQLite with a clear upgrade path to PostgreSQL. The database is initialized and managed through the `MigrationManager` class which tracks schema versions and applies incremental migrations.

## Schema Versioning

The `schema_version` table tracks all applied migrations:

```
schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
)
```

This table enables:
- Tracking of applied migrations
- Prevention of duplicate migrations
- Clear audit trail of schema changes

## Migrations

All database schema changes are organized as numbered SQL migration files in `database/migrations/`:

| Version | File | Purpose |
|---------|------|---------|
| 001 | 001_initial_schema.sql | Initial schema: wallets, transactions, network_configs, wallet_tags, ai_memory, command_history |
| 002 | 002_add_indexes.sql | Strategic indexes for query optimization |
| 003 | 003_add_transaction_queue.sql | Transaction queue table for retry logic |
| 004 | 004_add_balance_cache.sql | Balance cache table for reducing RPC calls |

## Tables

### Core Tables

#### wallets
Stores wallet information:
```
- id (INTEGER PRIMARY KEY)
- address (TEXT UNIQUE NOT NULL)
- private_key (TEXT NOT NULL)
```

#### transactions
Records all transactions:
```
- id (INTEGER PRIMARY KEY)
- tx_hash (TEXT UNIQUE)
- sender (TEXT NOT NULL) - with index for efficient lookups
- receiver (TEXT NOT NULL) - with index for efficient lookups
- amount_wei (TEXT NOT NULL)
- amount_display (TEXT NOT NULL)
- chain (TEXT NOT NULL) - with index for chain/status filtering
- status (TEXT NOT NULL)
- gas_used (INTEGER)
- gas_price_wei (TEXT)
- nonce (INTEGER)
- explorer_url (TEXT)
- error_message (TEXT)
- created_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
```

#### network_configs
Network/chain configuration:
```
- key (TEXT PRIMARY KEY)
- name (TEXT NOT NULL)
- rpc_url (TEXT NOT NULL)
- explorer (TEXT NOT NULL)
- native_token (TEXT NOT NULL)
- decimals (INTEGER NOT NULL)
- chain_id (INTEGER NOT NULL)
- is_active (INTEGER NOT NULL DEFAULT 1)
- created_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
- updated_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
```

#### wallet_tags
User-defined tags for wallets:
```
- wallet_id (INTEGER NOT NULL FK)
- tag (TEXT NOT NULL)
- created_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
```

#### ai_memory
AI system memory and preferences:
```
- id (INTEGER PRIMARY KEY)
- memory_key (TEXT NOT NULL)
- memory_type (TEXT NOT NULL DEFAULT 'generic')
- memory_value (TEXT NOT NULL)
- metadata_json (TEXT)
- created_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
- updated_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
```

#### command_history
Historical log of CLI commands:
```
- id (INTEGER PRIMARY KEY)
- prompt (TEXT NOT NULL)
- parsed_intent (TEXT)
- outcome (TEXT NOT NULL)
- wallet_ref (TEXT)
- chain (TEXT)
- export_format (TEXT)
- created_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
```

### Performance Tables (New)

#### transaction_queue
Queues pending transactions for retry logic:
```
- id (INTEGER PRIMARY KEY)
- tx_hash (TEXT UNIQUE NOT NULL)
- wallet_address (TEXT NOT NULL FK)
- chain (TEXT NOT NULL)
- status (TEXT NOT NULL DEFAULT 'pending')
- retry_count (INTEGER NOT NULL DEFAULT 0)
- max_retries (INTEGER NOT NULL DEFAULT 5)
- last_attempt_at (TEXT)
- next_retry_at (TEXT)
- error_message (TEXT)
- metadata_json (TEXT)
- created_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
- updated_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
```

Index: (status, next_retry_at) - for efficient queue processing
Index: (chain, status) - for chain-specific filtering
Index: (wallet_address) - for wallet-specific queries

#### balance_cache
Caches wallet balances to reduce RPC calls:
```
- id (INTEGER PRIMARY KEY)
- wallet_address (TEXT NOT NULL FK)
- chain (TEXT NOT NULL)
- balance_wei (TEXT NOT NULL)
- updated_at (TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)
- UNIQUE(wallet_address, chain)
```

Index: (wallet_address, chain) - for efficient cache lookups
Index: (updated_at DESC) - for cache expiration queries

## Views

### tx_history
Provides a clean interface to transaction data:
```
SELECT
    id, tx_hash, sender, receiver, amount_wei, amount_display,
    chain, status, gas_used, gas_price_wei, nonce,
    explorer_url, error_message, created_at
FROM transactions
```

## Indexes

Strategic indexes are created to optimize common query patterns:

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| idx_transactions_sender_created | transactions | (sender, created_at DESC) | Historical queries by sender |
| idx_transactions_receiver_created | transactions | (receiver, created_at DESC) | Historical queries by receiver |
| idx_transactions_chain_status | transactions | (chain, status) | Filter by chain and status |
| idx_transactions_tx_hash | transactions | (tx_hash) | Transaction lookup |
| idx_wallet_tags_wallet_id | wallet_tags | (wallet_id) | Reverse lookup joins |
| idx_wallet_tags_tag | wallet_tags | (tag) | Tag-based lookups |
| idx_ai_memory_key_type | ai_memory | (memory_key, memory_type) | Memory queries |
| idx_command_history_created | command_history | (created_at DESC) | Recent command queries |
| idx_command_history_wallet_ref | command_history | (wallet_ref) | Command history by wallet |
| idx_network_configs_active | network_configs | (is_active) | Active network filtering |
| idx_transaction_queue_status_retry | transaction_queue | (status, next_retry_at) | Queue processing |
| idx_transaction_queue_chain_status | transaction_queue | (chain, status) | Chain-specific queue filtering |
| idx_transaction_queue_wallet_address | transaction_queue | (wallet_address) | Wallet-specific transactions |
| idx_balance_cache_wallet_chain | balance_cache | (wallet_address, chain) | Cache lookups |
| idx_balance_cache_updated | balance_cache | (updated_at DESC) | Cache expiration |

## Migration Framework

### Running Migrations

Migrations are automatically applied when:
1. `DatabaseManager.migrate()` is called
2. `database.migrations.migrate()` is called directly

The migration system is idempotent - it only applies new migrations based on the version in the `schema_version` table.

### Adding New Migrations

To add a new migration:

1. Create a new SQL file in `database/migrations/` with the pattern `NNN_description.sql` where NNN is the next version number
2. Write portable SQL (see PostgreSQL compatibility notes below)
3. The MigrationManager will automatically pick it up and apply it

Example:
```sql
-- database/migrations/005_add_new_feature.sql
CREATE TABLE IF NOT EXISTS new_feature_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_new_feature_created 
    ON new_feature_table(created_at DESC);
```

## PostgreSQL Compatibility

Papa is designed with PostgreSQL migration in mind. Current deployment uses SQLite, but the architecture supports migration to PostgreSQL.

### Current SQLite-Specific Patterns

These patterns should be updated when migrating to PostgreSQL:

| SQLite | PostgreSQL |
|--------|-----------|
| INTEGER PRIMARY KEY AUTOINCREMENT | SERIAL PRIMARY KEY or INTEGER GENERATED BY DEFAULT AS IDENTITY |
| TEXT | VARCHAR or TEXT depending on field |
| DEFAULT CURRENT_TIMESTAMP | DEFAULT CURRENT_TIMESTAMP (compatible) |
| CREATE TABLE IF NOT EXISTS | CREATE TABLE IF NOT EXISTS (supported in PostgreSQL 9.1+) |
| CREATE INDEX IF NOT EXISTS | CREATE INDEX IF NOT EXISTS (supported in PostgreSQL 9.5+) |

### Migration Path to PostgreSQL

1. **Prepare**: Create PostgreSQL-compatible migration scripts in `database/migrations_pg/`
2. **Test**: Test migrations on PostgreSQL with equivalent data
3. **Configuration**: Add database dialect detection (SQLite vs PostgreSQL)
4. **Runtime**: Update `MigrationManager` to use appropriate migration directory
5. **Deploy**: Migrate production data using tools like pgLoader

### Database Abstraction Layer

Consider implementing a database dialect layer in the future:

```python
class DatabaseDialect:
    def pk_definition(self) -> str:
        """Primary key definition"""
        pass
    
    def timestamp_function(self) -> str:
        """Current timestamp function"""
        pass
```

## Consolidated Migration Calls

Migration calls are consolidated at application startup to avoid redundant operations:

- **papa.py**: Uses `_init_db_once()` to cache DatabaseManager instances for the default database path
- **ai/tools.py**: Uses `_init_db()` with path-based caching to reuse instances

Both approaches ensure migrations are only applied once per database path, even if the functions are called multiple times during application execution.

## Backward Compatibility

The migration framework is backward compatible with databases created before the migration system:

1. If `schema_version` table doesn't exist, it's created automatically
2. All migrations use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`
3. Existing data is preserved during migration
4. Version tracking starts from 0 if no prior migrations were recorded

## Query Performance

The strategic indexes enable efficient queries for:

- Transaction lookups by sender/receiver
- Chain-specific filtering
- Recent command history
- Active network configuration queries
- Transaction queue processing with exponential backoff
- Balance cache lookups with TTL-based expiration

Query performance should be measured after production deployment to identify any additional indexing needs.

## Future Enhancements

1. **Database Statistics**: Add query statistics collection for performance monitoring
2. **Connection Pooling**: Implement connection pooling for better resource utilization
3. **Read Replicas**: Support read replicas for horizontal scaling
4. **Sharding Strategy**: Design sharding strategy for horizontal scaling with multiple chains
5. **Audit Logging**: Add audit trail for sensitive operations (wallet key access, transactions)
6. **Data Retention**: Implement data retention policies for old transaction records
7. **Backup Strategy**: Define and test backup/restore procedures
