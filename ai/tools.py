"""Centralized AI tool registry with typed schemas and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal, List

from sqlalchemy import text

from utils.helpers import load_settings
from wallet.balance import BalanceResult, BalanceService
from wallet.database import DatabaseManager
from wallet.exporter import export_wallets as export_wallets_service
from wallet.generator import generate_wallets as generate_wallets_service
from wallet.tx_sender import SendResult, TransactionSender

ToolName = Literal[
    "generate_wallets",
    "send_transaction",
    "export_wallets",
    "show_balances",
    "show_transactions",
]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Structured tool-call envelope accepted by the dispatcher."""

    tool: ToolName
    args: Dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Declarative schema + executor binding for a tool."""

    name: ToolName
    schema: Dict[str, type]
    executor: Callable[..., Any]


def _default_db_path() -> str:
    settings = load_settings()
    return str(settings["database_path"])


def _init_db(db_path: str | None = None) -> DatabaseManager:
    db = DatabaseManager(db_path=db_path)
    db.migrate()
    return db


def _resolve_chain(db: DatabaseManager, chain: str | None) -> str:
    if chain:
        return chain
    preferred = db.get_preferred_chain()
    if preferred:
        return preferred
    settings = load_settings()
    return str(settings["default_chain"])


def _balance_to_dict(result: BalanceResult) -> Dict[str, Any]:
    return {
        "wallet_id": result.wallet_id,
        "address": result.address,
        "chain": result.chain,
        "balance_wei": result.balance_wei,
        "formatted": result.formatted,
    }


def _send_result_to_dict(result: SendResult) -> Dict[str, Any]:
    return {
        "tx_hash": result.tx_hash,
        "explorer_url": result.explorer_url,
        "chain": result.chain,
        "sender": result.sender,
        "receiver": result.receiver,
        "amount_wei": result.amount_wei,
        "status": result.status,
    }


def _tag_recent_wallets(db: DatabaseManager, count: int, tag: str) -> List[int]:
    if count <= 0:
        return []
    with db.engine.begin() as conn:
        ids = conn.execute(
            text("SELECT id FROM wallets ORDER BY id DESC LIMIT :limit"),
            {"limit": count},
        ).scalars().all()
    tagged_ids = [int(wallet_id) for wallet_id in ids]
    for wallet_id in tagged_ids:
        db.add_wallet_tag(wallet_id, tag)
    return tagged_ids


def _wallet_address(db: DatabaseManager, wallet_id: int) -> str:
    with db.engine.begin() as conn:
        row = conn.execute(
            text("SELECT address FROM wallets WHERE id = :id"),
            {"id": wallet_id},
        ).mappings().first()
    if not row:
        raise ValueError(f"Wallet id {wallet_id} not found")
    return str(row["address"])


def _generate_wallets(*, count: int, tag: str | None = None) -> Dict[str, Any]:
    db_path = _default_db_path()
    db = _init_db(db_path)
    generated = generate_wallets_service(count=count, db_path=db_path)
    tagged_ids: List[int] = []
    if tag:
        tagged_ids = _tag_recent_wallets(db, generated, tag)
    return {
        "action": "generate_wallets",
        "count": generated,
        "tag": tag,
        "tagged_wallet_ids": tagged_ids,
        "db_path": db_path,
    }


def _send_transaction(*, from_wallet: int, to_wallet: int, amount: str) -> Dict[str, Any]:
    db_path = _default_db_path()
    db = _init_db(db_path)
    chain_key = _resolve_chain(db, None)
    receiver = _wallet_address(db, to_wallet)
    tx_sender = TransactionSender(db)
    result = tx_sender.send_native(
        from_wallet=str(from_wallet),
        to_address=receiver,
        amount=amount,
        chain_key=chain_key,
    )
    return {
        "action": "send_transaction",
        "from_wallet": from_wallet,
        "to_wallet": to_wallet,
        "amount": amount,
        "chain": chain_key,
        "result": _send_result_to_dict(result),
    }


def _export_wallets(*, format: str) -> Dict[str, Any]:
    db_path = _default_db_path()
    exported_path = export_wallets_service(fmt=format, db_path=db_path)
    return {"action": "export_wallets", "format": format, "path": exported_path}


def _show_balances(*, wallet: int | None = None, chain: str | None = None) -> Dict[str, Any]:
    db_path = _default_db_path()
    db = _init_db(db_path)
    chain_key = _resolve_chain(db, chain)
    balances = BalanceService(db)
    if wallet is None:
        wallet_rows = db.list_wallets(limit=20)
        wallet_refs = [str(row["id"]) for row in wallet_rows]
        results = balances.get_multi_wallet_balances(wallet_refs, chain_key) if wallet_refs else []
    else:
        results = [balances.get_wallet_balance(str(wallet), chain_key)]
    return {
        "action": "show_balances",
        "chain": chain_key,
        "wallet": wallet,
        "count": len(results),
        "balances": [_balance_to_dict(result) for result in results],
    }


def _show_transactions(*, limit: int = 20) -> Dict[str, Any]:
    db_path = _default_db_path()
    db = _init_db(db_path)
    transactions = db.list_transactions(limit=limit)
    return {
        "action": "show_transactions",
        "limit": limit,
        "count": len(transactions),
        "transactions": transactions,
    }


TOOL_REGISTRY: Dict[ToolName, ToolSpec] = {
    "generate_wallets": ToolSpec(
        name="generate_wallets",
        schema={"count": int, "tag": (str, type(None))},
        executor=_generate_wallets,
    ),
    "send_transaction": ToolSpec(
        name="send_transaction",
        schema={"from_wallet": int, "to_wallet": int, "amount": str},
        executor=_send_transaction,
    ),
    "export_wallets": ToolSpec(
        name="export_wallets",
        schema={"format": str},
        executor=_export_wallets,
    ),
    "show_balances": ToolSpec(
        name="show_balances",
        schema={"wallet": (int, type(None)), "chain": (str, type(None))},
        executor=_show_balances,
    ),
    "show_transactions": ToolSpec(
        name="show_transactions",
        schema={"limit": int},
        executor=_show_transactions,
    ),
}


def validate_tool_call(call: ToolCall) -> None:
    """Validate tool name and argument types against the registry."""
    spec = TOOL_REGISTRY.get(call.tool)
    if spec is None:
        raise ValueError(f"Unknown tool: {call.tool}")

    for key, expected_type in spec.schema.items():
        if key not in call.args:
            raise ValueError(f"Missing required argument: {key}")
        if not isinstance(call.args[key], expected_type):
            raise TypeError(f"Invalid type for '{key}': expected {expected_type}, got {type(call.args[key])}")

    extra = set(call.args).difference(spec.schema)
    if extra:
        raise ValueError(f"Unexpected arguments for {call.tool}: {sorted(extra)}")


def execute_tool_call(call: ToolCall) -> Any:
    """Execute a validated, structured tool call via the registry."""
    validate_tool_call(call)
    spec = TOOL_REGISTRY[call.tool]
    return spec.executor(**call.args)
