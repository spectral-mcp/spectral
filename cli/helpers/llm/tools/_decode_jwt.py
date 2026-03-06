"""LLM tool: decode a JWT token (without signature verification)."""

from __future__ import annotations

import base64
from collections.abc import Callable
import json
from typing import Any

from cli.helpers.json import minified

NAME = "decode_jwt"

DEFINITION: dict[str, Any] = {
    "name": NAME,
    "description": "Decode a JWT token (without signature verification). Returns the decoded header and payload as JSON.",
    "input_schema": {
        "type": "object",
        "properties": {
            "token": {
                "type": "string",
                "description": "The JWT token string (header.payload.signature).",
            }
        },
        "required": ["token"],
    },
}


def execute(token: str) -> str:
    """Decode a JWT header + payload (no signature verification)."""
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("Invalid JWT: expected at least 2 dot-separated parts")
    decoded: dict[str, Any] = {}
    for label, part in zip(("header", "payload"), parts[:2]):
        padded = part + "=" * (-len(part) % 4)
        raw = base64.urlsafe_b64decode(padded)
        decoded[label] = json.loads(raw)
    return minified(decoded)


def make_executor(
    *, traces: Any = None, contexts: Any = None,
) -> Callable[[dict[str, Any]], str]:
    return lambda inp: execute(inp["token"])
