"""LLM tool: URL-decode a percent-encoded string."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import unquote

NAME = "decode_url"

DEFINITION: dict[str, Any] = {
    "name": NAME,
    "description": "URL-decode a percent-encoded string (e.g. %20 → space, %2F → /).",
    "input_schema": {
        "type": "object",
        "properties": {
            "value": {
                "type": "string",
                "description": "The percent-encoded string to decode.",
            }
        },
        "required": ["value"],
    },
}


def execute(value: str) -> str:
    """URL-decode a percent-encoded string."""
    return unquote(value)


def make_executor(
    *, traces: Any = None, contexts: Any = None,
) -> Callable[[dict[str, Any]], str]:
    return lambda inp: execute(inp["value"])
