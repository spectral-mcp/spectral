"""Tool registry and factory for LLM tool-use.

Each tool module in this package exposes:
- ``NAME: str`` — tool name
- ``DEFINITION: dict`` — tool schema
- ``make_executor(*, traces, contexts) -> Callable`` — returns the executor closure
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any

from cli.commands.capture.types import CaptureBundle, Context, Trace
from cli.helpers.llm.tools import (
    _decode_base64,
    _decode_jwt,
    _decode_url,
    _infer_request_schema,
    _inspect_context,
    _inspect_request,
    _inspect_trace,
    _query_traces,
)

_REGISTRY: dict[str, ModuleType] = {
    _decode_base64.NAME: _decode_base64,
    _decode_url.NAME: _decode_url,
    _decode_jwt.NAME: _decode_jwt,
    _inspect_trace.NAME: _inspect_trace,
    _inspect_request.NAME: _inspect_request,
    _inspect_context.NAME: _inspect_context,
    _infer_request_schema.NAME: _infer_request_schema,
    _query_traces.NAME: _query_traces,
}


def execute_tool(
    block: Any,
    executors: dict[str, Callable[[dict[str, Any]], str]],
) -> tuple[dict[str, Any], str, bool]:
    """Execute a single tool_use block, returning ``(tool_result, result_str, is_error)``."""
    executor = executors.get(block.name)
    if executor is None:
        result_str = f"Unknown tool: {block.name}"
        is_error = True
    else:
        try:
            result_str = executor(block.input)
            is_error = False
        except Exception as exc:
            result_str = f"Error: {exc}"
            is_error = True

    tool_result: dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": result_str,
    }
    if is_error:
        tool_result["is_error"] = True

    return tool_result, result_str, is_error


def make_tools(
    names: Sequence[str],
    bundle: CaptureBundle | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Callable[[dict[str, Any]], str]]]:
    """Build tool definitions and executors for the given tool names.

    Returns ``(tool_definitions, executors)`` for use with ``Conversation``.
    """
    traces: list[Trace] | None = bundle.traces if bundle is not None else None
    contexts: list[Context] | None = bundle.contexts if bundle is not None else None

    definitions: list[dict[str, Any]] = []
    executors: dict[str, Callable[[dict[str, Any]], str]] = {}

    for name in names:
        mod = _REGISTRY.get(name)
        if mod is None:
            raise ValueError(f"Unknown tool: {name!r}. Available: {sorted(_REGISTRY)}")
        definitions.append(mod.DEFINITION)  # pyright: ignore[reportAttributeAccessIssue]
        executors[name] = mod.make_executor(traces=traces, contexts=contexts)  # pyright: ignore[reportAttributeAccessIssue]

    return definitions, executors


# Convenience: all tool names
ALL_TOOL_NAMES = list(_REGISTRY.keys())
MCP_TOOL_NAMES = [
    "decode_base64", "decode_url", "decode_jwt",
    "inspect_request", "inspect_trace",
    "infer_request_schema", "query_traces",
]
