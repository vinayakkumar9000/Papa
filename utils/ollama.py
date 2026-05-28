"""Ollama runtime/service checks for AI CLI commands."""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.request

OLLAMA_API_TAGS = "http://127.0.0.1:11434/api/tags"


class OllamaError(RuntimeError):
    """Raised when Ollama setup/checks fail."""


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def is_reachable(timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_API_TAGS, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def _start_service() -> None:
    os_name = platform.system().lower()
    if os_name == "linux" and shutil.which("systemctl"):
        _run(["systemctl", "enable", "--now", "ollama"])
        return

    if os_name == "darwin" and shutil.which("brew"):
        _run(["brew", "services", "start", "ollama"])
        return

    _run(["bash", "-lc", "nohup ollama serve >/tmp/ollama.log 2>&1 &"], check=False)


def ensure_daemon(max_wait_seconds: int = 25) -> None:
    if not shutil.which("ollama"):
        raise OllamaError("Ollama is not installed. Run ./setup/install.sh first.")

    if is_reachable():
        return

    _start_service()
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        if is_reachable():
            return
        time.sleep(1)

    raise OllamaError(
        "Ollama daemon is not reachable at 127.0.0.1:11434 after startup attempts. "
        "Check service status/logs and rerun setup/install.sh."
    )


def ensure_model(model: str) -> None:
    ensure_daemon()
    listed = _run(["ollama", "list"]).stdout
    if model not in listed:
        _run(["ollama", "pull", model])
        listed = _run(["ollama", "list"]).stdout
        if model not in listed:
            raise OllamaError(f"Model '{model}' is not available after pull.")
