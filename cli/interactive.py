"""Interactive AI terminal for `papa ai` style sessions."""

from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console

from ai.autonomous import AutonomousController


console = Console()


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
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]{exc}[/red]")
