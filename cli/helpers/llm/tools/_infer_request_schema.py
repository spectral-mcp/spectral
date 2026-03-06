"""LLM tool: merge request bodies into an annotated JSON Schema."""

from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any, cast

from cli.commands.capture.types import Trace
from cli.helpers.json import minified
from cli.helpers.schema import infer_schema

NAME = "infer_request_schema"

DEFINITION: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Merge request bodies from the given trace IDs into an annotated JSON Schema. "
        "Shows which fields vary (parameters) vs stay the same (fixed values) "
        "across traces, with up to 5 example values per field."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "trace_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of trace IDs whose request bodies to merge.",
            },
        },
        "required": ["trace_ids"],
    },
}


def execute(inp: dict[str, Any], index: dict[str, Trace]) -> str:
    trace_ids: list[str] = inp["trace_ids"]
    samples: list[dict[str, Any]] = []
    for tid in trace_ids:
        trace = index.get(tid)
        if trace is None:
            continue
        if trace.request_body:
            try:
                body: Any = json.loads(trace.request_body)
                if isinstance(body, dict):
                    samples.append(cast(dict[str, Any], body))
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

    if not samples:
        return "No JSON request bodies found for the given trace IDs."

    schema = infer_schema(samples)
    return minified(schema)


def make_executor(
    *, traces: list[Trace] | None = None, contexts: Any = None,
) -> Callable[[dict[str, Any]], str]:
    if traces is None:
        raise ValueError("infer_request_schema requires traces")
    index = {t.meta.id: t for t in traces}
    return lambda inp: execute(inp, index)
