"""Gas strategy and transaction gas parameter utilities."""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from web3 import Web3


class GasManager:
    """Resolve gas price and gas limit for EVM transactions."""

    def __init__(self, default_limit: int = 21000):
        self.default_limit = default_limit
        self.logger = logging.getLogger(__name__)

    def resolve(self, w3: Web3, tx_base: dict, gas_limit: Optional[int], gas_price_wei: Optional[int]) -> Tuple[int, int]:
        """Resolve gas limit and gas price for a transaction."""
        resolved_gas_price = gas_price_wei if gas_price_wei is not None else int(w3.eth.gas_price)
        if gas_limit is not None:
            return gas_limit, resolved_gas_price

        try:
            estimated = int(w3.eth.estimate_gas(tx_base))
            return max(estimated, self.default_limit), resolved_gas_price
        except Exception as exc:
            self.logger.warning("Gas estimation failed, using default limit: %s", exc)
            return self.default_limit, resolved_gas_price
