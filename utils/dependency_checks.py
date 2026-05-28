"""Dependency validation utilities for bootstrap and doctor flows."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import Dict, List

REQUIRED_PACKAGES: Dict[str, str] = {
    "eth-account": "0.11.0",
    "web3": "6.15.1",
    "ollama": "0.3.3",
    "typer": "0.12.3",
    "rich": "13.7.1",
    "prompt-toolkit": "3.0.47",
    "SQLAlchemy": "2.0.32",
    "aiohttp": "3.13.5",
    "pydantic": "2.8.2",
    "python-dotenv": "1.0.1",
    "PyYAML": "6.0.2",
    "cryptography": "43.0.1",
}

IMPORT_NAMES: Dict[str, str] = {
    "eth-account": "eth_account",
    "web3": "web3",
    "ollama": "ollama",
    "typer": "typer",
    "rich": "rich",
    "prompt-toolkit": "prompt_toolkit",
    "SQLAlchemy": "sqlalchemy",
    "aiohttp": "aiohttp",
    "pydantic": "pydantic",
    "python-dotenv": "dotenv",
    "PyYAML": "yaml",
    "cryptography": "cryptography",
}


def validate_dependencies() -> List[str]:
    """Return a list of validation errors for required dependencies."""
    errors: List[str] = []

    for package, expected in REQUIRED_PACKAGES.items():
        try:
            installed = version(package)
        except PackageNotFoundError:
            errors.append(f"Missing package: {package}=={expected}")
            continue

        if installed != expected:
            errors.append(f"Version mismatch for {package}: expected {expected}, found {installed}")

        import_name = IMPORT_NAMES[package]
        try:
            import_module(import_name)
        except Exception as exc:  # pragma: no cover - surface runtime import problems
            errors.append(f"Import failed for {package} ({import_name}): {exc}")

    try:
        web3_version = version("web3")
        eth_account_version = version("eth-account")
        if web3_version != REQUIRED_PACKAGES["web3"] or eth_account_version != REQUIRED_PACKAGES["eth-account"]:
            errors.append(
                "web3/eth-account compatibility policy requires web3==6.15.1 and eth-account==0.11.0"
            )
    except PackageNotFoundError:
        pass

    return errors
