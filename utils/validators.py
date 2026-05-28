"""Input validation and unit parsing utilities."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from web3 import Web3

_AMOUNT_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(wei|gwei|ether)?\s*$", re.IGNORECASE)


def validate_address(address: str) -> str:
    """Validate and checksum an EVM address."""
    if not Web3.is_address(address):
        raise ValueError(f"Invalid EVM address: {address}")
    return Web3.to_checksum_address(address)


def parse_amount_to_wei(amount: str, decimals: int = 18) -> int:
    """Parse amount strings like 1wei, 1gwei, 0.1ether to wei."""
    match = _AMOUNT_RE.match(amount)
    if not match:
        raise ValueError("Amount must be like 1wei, 1gwei, or 0.0001ether")

    number_raw, unit_raw = match.groups()
    unit = (unit_raw or "ether").lower()

    try:
        number = Decimal(number_raw)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid amount value: {amount}") from exc

    if number <= 0:
        raise ValueError("Amount must be greater than zero")

    if unit == "wei":
        return int(number)
    if unit == "gwei":
        return int(number * Decimal(10**9))
    if unit == "ether":
        return int(number * Decimal(10**decimals))

    raise ValueError(f"Unsupported unit: {unit}")
