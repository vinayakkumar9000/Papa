-- Wallet Database Export
-- Source Database: export_test.db
-- Exported: 2026-05-30 09:36:57

CREATE TABLE IF NOT EXISTS wallets (
    id INTEGER PRIMARY KEY,
    address TEXT NOT NULL,
    private_key TEXT NOT NULL
);

INSERT INTO wallets (id, address, private_key) VALUES (1, '0x1234567890abcdef1234567890abcdef12345678', '0xprivkey1');
INSERT INTO wallets (id, address, private_key) VALUES (2, '0xabcdefabcdefabcdefabcdefabcdefabcdefabcd', '0xprivkey2');
