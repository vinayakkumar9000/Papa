#!/usr/bin/env python3
"""Bootstrap Ollama runtime and model availability."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.request

OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://127.0.0.1:11434/api/tags"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def is_ollama_reachable(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def wait_for_ollama(max_wait: int = 30) -> bool:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if is_ollama_reachable():
            return True
        time.sleep(1)
    return False


def install_ollama_linux() -> None:
    print("[bootstrap] Installing Ollama for Linux...")
    run(["bash", "-lc", "curl -fsSL https://ollama.com/install.sh | sh"])


def install_ollama_macos() -> None:
    if shutil.which("brew"):
        print("[bootstrap] Installing Ollama with Homebrew...")
        run(["brew", "install", "ollama"])
    else:
        raise RuntimeError("Homebrew not found. Install Ollama manually from https://ollama.com/download")


def ensure_ollama_installed() -> None:
    if shutil.which("ollama"):
        return

    system = platform.system().lower()
    if system == "linux":
        install_ollama_linux()
    elif system == "darwin":
        install_ollama_macos()
    else:
        raise RuntimeError(f"Unsupported OS for automatic Ollama installation: {platform.system()}")

    if not shutil.which("ollama"):
        raise RuntimeError("Ollama installation did not provide `ollama` on PATH")


def start_service_linux() -> None:
    if shutil.which("systemctl"):
        print("[bootstrap] Enabling and starting ollama.service via systemd...")
        run(["systemctl", "enable", "--now", "ollama"])
        return

    print("[bootstrap] systemd unavailable. Starting fallback daemon with nohup...")
    run(["bash", "-lc", "nohup ollama serve >/tmp/ollama.log 2>&1 &"], check=False)


def start_service_macos() -> None:
    if shutil.which("brew"):
        print("[bootstrap] Starting Ollama as a Homebrew service...")
        run(["brew", "services", "start", "ollama"])
        return

    print("[bootstrap] Homebrew services unavailable. Starting fallback daemon with nohup...")
    run(["bash", "-lc", "nohup ollama serve >/tmp/ollama.log 2>&1 &"], check=False)


def ensure_daemon_running() -> None:
    if is_ollama_reachable():
        print("[bootstrap] Ollama daemon already reachable")
        return

    system = platform.system().lower()
    if system == "linux":
        start_service_linux()
    elif system == "darwin":
        start_service_macos()
    else:
        print("[bootstrap] Unsupported OS for service managers; attempting direct daemon fallback...")
        run(["bash", "-lc", "nohup ollama serve >/tmp/ollama.log 2>&1 &"], check=False)

    if not wait_for_ollama():
        raise RuntimeError("Ollama daemon failed to become reachable on 127.0.0.1:11434")


def ensure_model_available(model: str = OLLAMA_MODEL) -> None:
    print(f"[bootstrap] Pulling model {model}...")
    run(["ollama", "pull", model])

    tags = run(["ollama", "list"]).stdout
    if model not in tags:
        raise RuntimeError(f"Model {model} not found after pull")


def main() -> None:
    ensure_ollama_installed()
    ensure_daemon_running()
    ensure_model_available()
    print("[bootstrap] Ollama bootstrap complete")


if __name__ == "__main__":
    main()
