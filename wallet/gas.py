"""Gas strategy and transaction gas parameter utilities."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from web3 import Web3


class GasManager:
    """Resolve gas price and gas limit for EVM transactions with fallback strategies."""

    def __init__(self, default_limit: int = 21000, safety_multiplier: float = 1.2):
        """
        Initialize gas manager.
        
        Args:
            default_limit: Default gas limit for simple transfers
            safety_multiplier: Multiplier applied to estimated gas (e.g., 1.2 = 20% buffer)
        """
        self.default_limit = default_limit
        self.safety_multiplier = max(1.0, safety_multiplier)  # Ensure >= 1.0
        self.logger = logging.getLogger(__name__)
        self._last_successful_gas: dict[str, int] = {}  # Cache of last successful estimates

    def resolve(
        self, w3: Web3, tx_base: dict, gas_limit: Optional[int], gas_price_wei: Optional[int]
    ) -> Tuple[int, int]:
        """
        Resolve gas limit and gas price for a transaction.
        
        Implements fallback strategy:
        1. Use provided gas limit if specified
        2. Try to estimate gas from transaction
        3. Fall back to cached successful estimate for similar tx
        4. Fall back to default limit
        
        Args:
            w3: Web3 instance
            tx_base: Base transaction object
            gas_limit: Explicit gas limit (if provided, used as-is)
            gas_price_wei: Explicit gas price in wei
            
        Returns:
            Tuple of (resolved_gas_limit, resolved_gas_price)
        """
        # Resolve gas price first (usually straightforward)
        resolved_gas_price = gas_price_wei if gas_price_wei is not None else self._get_gas_price(w3)

        # If explicit gas limit provided, use it
        if gas_limit is not None:
            return gas_limit, resolved_gas_price

        # Try to estimate
        estimated = self._estimate_gas_with_retry(w3, tx_base)
        if estimated is not None:
            # Apply safety multiplier for estimated gas
            safe_limit = int(estimated * self.safety_multiplier)
            return max(safe_limit, self.default_limit), resolved_gas_price

        # Use fallback strategy
        fallback_limit = self._get_fallback_limit(tx_base)
        return fallback_limit, resolved_gas_price

    def _get_gas_price(self, w3: Web3) -> int:
        """
        Get current gas price with fallback.
        
        Args:
            w3: Web3 instance
            
        Returns:
            Gas price in wei
        """
        try:
            return int(w3.eth.gas_price)
        except Exception as exc:
            self.logger.warning("Failed to get gas price: %s, using 1 gwei fallback", exc)
            # 1 gwei fallback
            return 1_000_000_000

    def _estimate_gas_with_retry(self, w3: Web3, tx_base: dict) -> Optional[int]:
        """
        Estimate gas with exponential backoff retry.
        
        Args:
            w3: Web3 instance
            tx_base: Transaction base
            
        Returns:
            Estimated gas or None if all attempts fail
        """
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                estimated = int(w3.eth.estimate_gas(tx_base))
                self.logger.debug("Gas estimation succeeded: %s wei", estimated)
                # Cache for fallback
                self._cache_gas_estimate(tx_base, estimated)
                return estimated
            except Exception as exc:
                self.logger.debug("Gas estimation attempt %d failed: %s", attempt + 1, exc)
                if attempt < max_attempts - 1:
                    # Small delay before retry (RPC may be temporarily overloaded)
                    import time

                    time.sleep(0.5)
        return None

    def _cache_gas_estimate(self, tx_base: dict, gas: int) -> None:
        """Cache a successful gas estimate for fallback."""
        # Create a cache key based on tx characteristics
        sender = tx_base.get("from", "unknown")[:10]
        to_addr = tx_base.get("to", "unknown")[:10]
        value = tx_base.get("value", 0)
        cache_key = f"{sender}_{to_addr}_{value > 0}"
        self._last_successful_gas[cache_key] = gas

    def _get_fallback_limit(self, tx_base: dict) -> int:
        """
        Get fallback gas limit based on cached estimates or transaction type.
        
        Args:
            tx_base: Transaction base
            
        Returns:
            Fallback gas limit
        """
        # Try to use cached estimate
        sender = tx_base.get("from", "unknown")[:10]
        to_addr = tx_base.get("to", "unknown")[:10]
        value = tx_base.get("value", 0)
        cache_key = f"{sender}_{to_addr}_{value > 0}"

        if cache_key in self._last_successful_gas:
            cached = self._last_successful_gas[cache_key]
            # Apply safety multiplier to cached value
            return int(cached * self.safety_multiplier)

        # Default fallback based on transaction type
        value = tx_base.get("value", 0)
        if value > 0:
            # Native transfer with value: 21000
            return self.default_limit
        else:
            # Contract call: use higher estimate
            return int(self.default_limit * 3)  # 63000

    def update_multiplier(self, multiplier: float) -> None:
        """
        Update the safety multiplier.
        
        Args:
            multiplier: New safety multiplier (must be >= 1.0)
        """
        if multiplier < 1.0:
            self.logger.warning("Safety multiplier must be >= 1.0, ignoring: %s", multiplier)
            return
        self.safety_multiplier = multiplier
        self.logger.info("Gas safety multiplier updated to: %s", multiplier)

    def clear_cache(self) -> None:
        """Clear cached gas estimates."""
        self._last_successful_gas.clear()
