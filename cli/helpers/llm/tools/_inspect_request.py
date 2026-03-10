"""LLM tool: inspect request-side details for a trace."""

from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any

from cli.commands.capture.types import Trace
from cli.helpers.http import sanitize_headers
from cli.helpers.json import minified, truncate_json

NAME = "inspect_request"

DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": NAME,
        "description": (
            "Get request-side details for a trace: method, URL, headers, "
            "and request body. Does NOT include the response. "
            "Use this first to understand what an endpoint expects. "
            "Only use inspect_trace if you also need the response body."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "trace_id": {
                    "type": "string",
                    "description": "The trace ID (e.g., 't_0001').",
                },
            },
            "required": ["trace_id"],
        },
    },
}


def execute(inp: dict[str, Any], index: dict[str, Trace]) -> str:
    trace = index.get(inp["trace_id"])
    if trace is None:
        return f"Trace {inp['trace_id']} not found"

    result: dict[str, Any] = {
        "method": trace.meta.request.method,
        "url": trace.meta.request.url,
        "status": trace.meta.response.status,
        "request_headers": sanitize_headers(
            {h.name: h.value for h in trace.meta.request.headers}
        ),
    }
    if trace.request_body:
        try:
            result["request_body"] = truncate_json(
                json.loads(trace.request_body), max_keys=20
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            result["request_body_raw"] = trace.request_body.decode(errors="replace")[
                :1000
            ]
    return minified(result)


def make_executor(
    *, traces: list[Trace] | None = None, contexts: Any = None,
) -> Callable[[dict[str, Any]], str]:
    if traces is None:
        raise ValueError("inspect_request requires traces")
    index = {t.meta.id: t for t in traces}
    return lambda inp: execute(inp, index)
