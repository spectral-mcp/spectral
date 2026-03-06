"""Debug logging helpers for LLM conversations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from cli.helpers.console import console
from cli.helpers.json import reformat_json_lines

_debug_dir: Path | None = None


def init_debug(*, debug: bool = False, debug_dir: Path | None = None) -> None:
    """Configure debug logging. Auto-creates a timestamped dir when debug=True."""
    global _debug_dir
    if debug and debug_dir is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        debug_dir = Path("debug") / ts
        debug_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"  Debug logs → {debug_dir}")
    _debug_dir = debug_dir


def clear_debug_dir() -> None:
    """Reset the debug directory (for tests)."""
    global _debug_dir
    _debug_dir = None


class DebugSession:
    """Accumulates debug turns for a single LLM call, appending to a file on each add."""

    def __init__(self, call_name: str):
        if _debug_dir is None:
            self._path: Path | None = None
        else:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            self._path = _debug_dir / f"{ts}_{call_name}"
        self._pending: list[str] = []

    def add_user(self, content: str) -> None:
        if self._path is None:
            return
        text = reformat_json_lines(str(content))
        self._append(f"=== PROMPT ===\n{text}\n")

    def add_assistant(self, text: str) -> None:
        if self._path is None:
            return
        text = reformat_json_lines(text)
        self._append(f"=== RESPONSE ===\n{text}\n")

    def add_tool_text(self, text: str) -> None:
        if self._path is None:
            return
        self._pending.append(f"=== ASSISTANT TEXT ===\n{text}")

    def add_tool_use(
        self, *, name: str, input: dict[str, Any], result: str, error: bool = False,
    ) -> None:
        if self._path is None:
            return
        inp = json.dumps(input, ensure_ascii=False)
        header = f"=== TOOL: {name}({inp}) ==="
        if error:
            header += " [ERROR]"
        self._pending.append(f"{header}\n{reformat_json_lines(result)}")

    def flush_tool_round(self) -> None:
        if self._path is None or not self._pending:
            return
        self._append("\n\n".join(self._pending) + "\n")
        self._pending.clear()

    def _append(self, text: str) -> None:
        assert self._path is not None
        with self._path.open("a") as f:
            f.write(text)
