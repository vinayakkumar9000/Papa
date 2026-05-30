"""Transaction sending engine for native token transfers with reliability enhancements."""

from __future__ import annotations

import time
from uuid import uuid4
from dataclasses import dataclass
from typing import Optional, List

from eth_account import Account
from web3 import Web3

from utils.formatters import format_native_amount
from utils.helpers import load_settings, setup_rotating_logger
from utils.validators import parse_amount_to_wei, validate_address
from wallet.chains import ChainRegistry
from wallet.database import DatabaseManager
from wallet.error_classifier import ErrorClassifier, ErrorType
from wallet.gas import GasManager
from wallet.models import TransactionRecord
from wallet.nonce import NonceManager
from wallet.rpc_manager import RpcManager


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
    """Send native EVM transactions with retries, RPC failover, and error classification."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.settings = load_settings()
        self.chain_registry = ChainRegistry(db)
        self.gas_manager = GasManager(
            default_limit=int(self.settings.get("gas", {}).get("default_limit", 21000)),
            safety_multiplier=float(self.settings.get("gas", {}).get("safety_multiplier", 1.2)),
        )
        self.logger = setup_rotating_logger("tx_sender", "tx.log")
        self.error_logger = setup_rotating_logger("tx_errors", "errors.log")
        self._rpc_managers: dict[str, RpcManager] = {}

    def _get_rpc_manager(self, chain_key: str, rpc_url: str) -> RpcManager:
        """
        Get or create an RPC manager for a chain.
        
        Args:
            chain_key: Chain identifier
            rpc_url: Primary RPC URL
            
        Returns:
            RpcManager instance
        """
        if chain_key not in self._rpc_managers:
            # For now, single RPC URL. Can be extended to support multiple URLs per chain
            rpc_urls = [rpc_url]
            timeout = int(self.settings.get("rpc_timeout", 20))
            self._rpc_managers[chain_key] = RpcManager(rpc_urls, timeout=timeout)
        return self._rpc_managers[chain_key]

    def _build_web3(self, chain_key: str, rpc_url: str) -> Web3:
        """
        Build Web3 instance with RPC failover support.
        
        Args:
            chain_key: Chain identifier
            rpc_url: Primary RPC URL
            
        Returns:
            Web3 instance connected to a healthy endpoint
        """
        rpc_manager = self._get_rpc_manager(chain_key, rpc_url)
        return rpc_manager.get_web3()

    def _should_retry(self, error: Exception) -> bool:
        """
        Determine if an error warrants a retry.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if the error is retryable
        """
        return ErrorClassifier.is_retryable(error)

    def _get_backoff_delay(self, error: Exception, attempt: int) -> float:
        """
        Calculate backoff delay for retry.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Delay in seconds
        """
        return ErrorClassifier.get_backoff_factor(error, attempt)

    def _classify_error(self, error: Exception) -> ErrorType:
        """
        Classify an error for logging and decision making.
        
        Args:
            error: The exception
            
        Returns:
            ErrorType classification
        """
        return ErrorClassifier.classify(error)

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
        """
        Send native token transaction and persist history.
        
        Features:
        - Automatic nonce management with concurrency safety
        - Error classification and intelligent retry
        - RPC failover support
        - Transaction history persistence
        
        Args:
            from_wallet: Source wallet reference (id, address, or tag)
            to_address: Destination address
            amount: Amount to transfer (e.g., "1wei", "1gwei", "0.1ether")
            chain_key: Chain identifier
            gas_limit: Optional gas limit override
            gas_price_wei: Optional gas price override
            nonce: Optional nonce override
            
        Returns:
            SendResult with transaction details
            
        Raises:
            RuntimeError: If transaction fails after all retries
            ConnectionError: If RPC connection fails
            ValueError: If chain configuration is invalid
        """
        chain = self.chain_registry.get(chain_key)
        sender_wallet = self.db.resolve_wallet(str(from_wallet))
        receiver = validate_address(to_address)

        # Connect to RPC with failover support
        w3 = self._build_web3(chain_key, chain.rpc_url)

        if not w3.is_connected():
            raise ConnectionError(f"RPC connection failed for {chain.name}")

        amount_wei = parse_amount_to_wei(amount, decimals=chain.decimals)
        actual_chain_id = int(w3.eth.chain_id)
        if actual_chain_id != chain.chain_id:
            raise ValueError(f"Chain mismatch: expected {chain.chain_id}, got {actual_chain_id}")

        # Configuration
        retries = max(1, int(self.settings.get("retry_count", 3)))
        backoff = float(self.settings.get("retry_backoff_seconds", 1.5))

        last_error: Optional[Exception] = None
        last_error_type: Optional[ErrorType] = None

        for attempt in range(1, retries + 1):
            try:
                # Get nonce with concurrency-safe management
                resolved_nonce = nonce if nonce is not None else NonceManager.next_nonce(w3, sender_wallet.address)

                tx_base = {
                    "from": sender_wallet.address,
                    "to": receiver,
                    "value": amount_wei,
                    "nonce": resolved_nonce,
                    "chainId": chain.chain_id,
                }

                # Resolve gas with fallback strategy
                resolved_gas_limit, resolved_gas_price = self.gas_manager.resolve(
                    w3,
                    tx_base,
                    gas_limit=gas_limit,
                    gas_price_wei=gas_price_wei,
                )
                tx_base["gas"] = resolved_gas_limit
                tx_base["gasPrice"] = resolved_gas_price

                # Sign and send transaction
                signed = Account.sign_transaction(tx_base, sender_wallet.private_key)
                tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction).hex()

                # Wait for receipt
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=int(self.settings.get("rpc_timeout", 20)))

                # Transaction succeeded
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
                last_error_type = self._classify_error(exc)
                should_retry = self._should_retry(exc)

                self.error_logger.error(
                    "send_attempt attempt=%s error_type=%s retryable=%s reason=%s",
                    attempt,
                    last_error_type.value,
                    should_retry,
                    str(exc),
                )

                if not should_retry:
                    # Permanent error, don't retry
                    self.logger.info("Permanent error encountered, not retrying: %s", exc)
                    break

                if attempt < retries:
                    # Calculate adaptive backoff
                    delay = self._get_backoff_delay(exc, attempt) or (backoff * attempt)
                    self.logger.debug("Retrying in %s seconds...", delay)
                    time.sleep(delay)

        # All retries exhausted, persist failure
        error_text = str(last_error) if last_error else "unknown error"
        error_type_str = last_error_type.value if last_error_type else "unknown"

        self.db.add_transaction(
            TransactionRecord(
                tx_hash=f"failed-{uuid4()}",
                sender=sender_wallet.address,
                receiver=receiver,
                amount_wei=amount_wei,
                amount_display=format_native_amount(amount_wei, chain.decimals, chain.native_token),
                chain=chain.key,
                status="failed",
                error_message=f"[{error_type_str}] {error_text}",
                nonce=nonce,
            )
        )

        raise RuntimeError(f"Transaction failed after {retries} attempts: [{error_type_str}] {error_text}")
