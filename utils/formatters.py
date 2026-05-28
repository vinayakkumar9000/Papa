"""Formatting helpers for CLI output and sensitive values."""

from __future__ import annotations

from decimal import Decimal


def mask_sensitive(value: str, visible: int = 4) -> str:
    """Mask sensitive values for logs and CLI output."""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def format_native_amount(wei_value: int, decimals: int = 18, token: str = "ETH") -> str:
    """Format wei integer to native token display value."""
    amount = Decimal(wei_value) / Decimal(10**decimals)
    return f"{amount.normalize()} {token}"
