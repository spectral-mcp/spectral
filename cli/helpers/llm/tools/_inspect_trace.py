"""LLM tool: inspect full request+response details for a trace."""

from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any

from cli.commands.capture.types import Trace
from cli.helpers.http import sanitize_headers
from cli.helpers.json import minified, truncate_json

NAME = "inspect_trace"

DEFINITION: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Get the full request and response details for a specific trace, "
        "including headers and decoded body content (JSON or text). "
        "Use this to examine login endpoints, token responses, OTP flows, etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "trace_id": {
                "type": "string",
                "description": "The trace ID (e.g., 't_0001').",
            },
        },
        "required": ["trace_id"],
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
        "response_headers": sanitize_headers(
            {h.name: h.value for h in trace.meta.response.headers}
        ),
    }
    if trace.request_body:
        try:
            result["request_body"] = truncate_json(
                json.loads(trace.request_body), max_keys=30
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            result["request_body_raw"] = trace.request_body.decode(errors="replace")[
                :2000
            ]
    if trace.response_body:
        try:
            result["response_body"] = truncate_json(
                json.loads(trace.response_body), max_keys=30
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            result["response_body_raw"] = trace.response_body.decode(errors="replace")[
                :2000
            ]
    serialized = minified(result)
    if len(serialized) > 4000:
        if trace.response_body:
            try:
                result["response_body"] = truncate_json(
                    json.loads(trace.response_body), max_keys=10, max_depth=2
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        serialized = minified(result)
    return serialized


def make_executor(
    *, traces: list[Trace] | None = None, contexts: Any = None,
) -> Callable[[dict[str, Any]], str]:
    if traces is None:
        raise ValueError("inspect_trace requires traces")
    index = {t.meta.id: t for t in traces}
    return lambda inp: execute(inp, index)
