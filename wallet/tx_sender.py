"""Transaction sending engine for native token transfers."""

from __future__ import annotations

import time
from uuid import uuid4
from dataclasses import dataclass
from typing import Optional

from eth_account import Account
from web3 import HTTPProvider, Web3

from utils.formatters import format_native_amount
from utils.helpers import load_settings, setup_rotating_logger
from utils.validators import parse_amount_to_wei, validate_address
from wallet.chains import ChainRegistry
from wallet.database import DatabaseManager
from wallet.gas import GasManager
from wallet.models import TransactionRecord
from wallet.nonce import NonceManager


@dataclass(slots=True)
class SendResult:
    """Result object for send operations."""

    tx_hash: str
    explorer_url: str
    chain: str
    sender: str
    receiver: str
    amount_wei: int
    status: str


class TransactionSender:
    """Send native EVM transactions with retries and DB history integration."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.settings = load_settings()
        self.chain_registry = ChainRegistry(db)
        self.gas_manager = GasManager(default_limit=int(self.settings.get("gas", {}).get("default_limit", 21000)))
        self.logger = setup_rotating_logger("tx_sender", "tx.log")
        self.error_logger = setup_rotating_logger("tx_errors", "errors.log")

    def _build_web3(self, rpc_url: str) -> Web3:
        timeout = int(self.settings.get("rpc_timeout", 20))
        return Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": timeout}))

    def send_native(
        self,
        from_wallet: str,
        to_address: str,
        amount: str,
        chain_key: str,
        gas_limit: Optional[int] = None,
        gas_price_wei: Optional[int] = None,
        nonce: Optional[int] = None,
    ) -> SendResult:
        """Send native token transaction and persist history."""
        chain = self.chain_registry.get(chain_key)
        sender_wallet = self.db.resolve_wallet(str(from_wallet))
        receiver = validate_address(to_address)
        w3 = self._build_web3(chain.rpc_url)

        if not w3.is_connected():
            raise ConnectionError(f"RPC connection failed for {chain.name}")

        amount_wei = parse_amount_to_wei(amount, decimals=chain.decimals)
        retries = max(1, int(self.settings.get("retry_count", 3)))
        backoff = float(self.settings.get("retry_backoff_seconds", 1.5))

        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                chain_id = int(w3.eth.chain_id)
                if chain_id != chain.chain_id:
                    raise ValueError(f"Chain mismatch: expected {chain.chain_id}, got {chain_id}")

                resolved_nonce = nonce if nonce is not None else NonceManager.next_nonce(w3, sender_wallet.address)
                tx_base = {
                    "from": sender_wallet.address,
                    "to": receiver,
                    "value": amount_wei,
                    "nonce": resolved_nonce,
                    "chainId": chain.chain_id,
                }

                resolved_gas_limit, resolved_gas_price = self.gas_manager.resolve(
                    w3,
                    tx_base,
                    gas_limit=gas_limit,
                    gas_price_wei=gas_price_wei,
                )
                tx_base["gas"] = resolved_gas_limit
                tx_base["gasPrice"] = resolved_gas_price

                signed = Account.sign_transaction(tx_base, sender_wallet.private_key)
                tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction).hex()
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=int(self.settings.get("rpc_timeout", 20)))

                explorer_url = f"{chain.explorer.rstrip('/')}/tx/{tx_hash}"
                status = "success" if int(receipt.get("status", 0)) == 1 else "failed"

                record = TransactionRecord(
                    tx_hash=tx_hash,
                    sender=sender_wallet.address,
                    receiver=receiver,
                    amount_wei=amount_wei,
                    amount_display=format_native_amount(amount_wei, chain.decimals, chain.native_token),
                    chain=chain.key,
                    status=status,
                    gas_used=int(receipt.get("gasUsed", 0)),
                    gas_price_wei=resolved_gas_price,
                    nonce=resolved_nonce,
                    explorer_url=explorer_url,
                )
                self.db.add_transaction(record)

                return SendResult(
                    tx_hash=tx_hash,
                    explorer_url=explorer_url,
                    chain=chain.key,
                    sender=sender_wallet.address,
                    receiver=receiver,
                    amount_wei=amount_wei,
                    status=status,
                )

            except Exception as exc:
                last_error = exc
                self.error_logger.error("send_failed attempt=%s reason=%s", attempt, str(exc))
                if attempt < retries:
                    time.sleep(backoff * attempt)

        error_text = str(last_error) if last_error else "unknown error"
        self.db.add_transaction(
            TransactionRecord(
                tx_hash=f"failed-{uuid4()}",
                sender=sender_wallet.address,
                receiver=receiver,
                amount_wei=amount_wei,
                amount_display=format_native_amount(amount_wei, chain.decimals, chain.native_token),
                chain=chain.key,
                status="failed",
                error_message=error_text,
                nonce=nonce,
            )
        )
        raise RuntimeError(f"Transaction failed after retries: {error_text}")
