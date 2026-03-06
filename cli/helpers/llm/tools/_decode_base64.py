"""LLM tool: decode a base64-encoded string."""

from __future__ import annotations

import base64
from collections.abc import Callable
import re
from typing import Any

NAME = "decode_base64"

DEFINITION: dict[str, Any] = {
    "name": NAME,
    "description": "Decode a base64-encoded string (standard or URL-safe, auto-padding). Returns the decoded text (UTF-8) or a hex dump if the content is binary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "value": {
                "type": "string",
                "description": "The base64-encoded string to decode.",
            }
        },
        "required": ["value"],
    },
}


def execute(value: str) -> str:
    """Decode a base64 string (standard or URL-safe, with auto-padding)."""
    padded = value + "=" * (-len(value) % 4)
    raw = None
    if re.fullmatch(r"[A-Za-z0-9\-_=]+", padded):
        try:
            raw = base64.urlsafe_b64decode(padded)
        except Exception:
            pass
    if raw is None and re.fullmatch(r"[A-Za-z0-9+/=]+", padded):
        try:
            raw = base64.b64decode(padded, validate=True)
        except Exception:
            pass
    if raw is None:
        raise ValueError(f"Cannot base64-decode: {value[:80]}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return f"<binary: {raw.hex()}>"


def make_executor(
    *, traces: Any = None, contexts: Any = None,
) -> Callable[[dict[str, Any]], str]:
    return lambda inp: execute(inp["value"])
