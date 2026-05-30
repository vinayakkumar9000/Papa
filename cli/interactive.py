"""Interactive AI terminal for `papa ai` style sessions."""

from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from ai.autonomous import AutonomousController
from ai.router import ConfirmationRequired
from ai.tools import ToolCall


console = Console()


_CONFIRMATION_MESSAGES = {
    "generate_wallets": "Confirm wallet generation?",
    "send_transaction": "Confirm sending transaction?",
    "export_wallets": "Confirm wallet export?",
}


def _confirmation_prompt(call: ToolCall) -> str:
    return _CONFIRMATION_MESSAGES.get(call.tool, f"Confirm {call.tool.replace('_', ' ')}?")


def _request_confirmation(session: PromptSession, call: ToolCall) -> bool:
    prompt = f"{_confirmation_prompt(call)} (y/n) "
    while True:
        response = session.prompt(prompt).strip().lower()
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        console.print("[yellow]Please respond with 'y' or 'n'.[/yellow]")


def launch_interactive() -> None:
    session = PromptSession(history=InMemoryHistory())
    controller = AutonomousController()
    console.print("[bold cyan]Papa AI terminal[/bold cyan] (type 'exit' to quit)")
    while True:
        prompt = session.prompt("papa-ai> ").strip()
        if prompt.lower() in {"exit", "quit"}:
            return
        if not prompt:
            continue
        try:
            result = controller.run(prompt)
            console.print(result)
        except ConfirmationRequired as exc:
            if not _request_confirmation(session, exc.call):
                console.print("[yellow]Action canceled.[/yellow]")
                continue
            try:
                result = controller.run_confirmed(exc.call)
                console.print(result)
            except Exception as confirm_exc:  # noqa: BLE001
                console.print(f"[red]{confirm_exc}[/red]")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]{exc}[/red]")
