"""LLM tool: inspect a UI context event."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cli.commands.capture.types import Context
from cli.helpers.json import minified, truncate_json

NAME = "inspect_context"

DEFINITION: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Get full details for a UI context event: action, element "
        "(tag, text, selector, attributes), page (url, title), "
        "and rich page content (headings, navigation, main text, "
        "forms, tables, alerts)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "context_id": {
                "type": "string",
                "description": "The context ID (e.g., 'c_0001').",
            },
        },
        "required": ["context_id"],
    },
}


def execute(inp: dict[str, Any], index: dict[str, Context]) -> str:
    ctx = index.get(inp["context_id"])
    if ctx is None:
        return f"Context {inp['context_id']} not found"

    result: dict[str, Any] = {
        "action": ctx.meta.action,
        "element": {
            "tag": ctx.meta.element.tag,
            "text": ctx.meta.element.text,
            "selector": ctx.meta.element.selector,
            "attributes": ctx.meta.element.attributes,
        },
        "page": {
            "url": ctx.meta.page.url,
            "title": ctx.meta.page.title,
        },
    }
    if ctx.meta.page.content is not None:
        content = ctx.meta.page.content
        result["page_content"] = truncate_json(
            {
                "headings": content.headings,
                "navigation": content.navigation,
                "main_text": content.main_text,
                "forms": content.forms,
                "tables": content.tables,
                "alerts": content.alerts,
            },
            max_keys=20,
        )
    return minified(result)


def make_executor(
    *, traces: Any = None, contexts: list[Context] | None = None,
) -> Callable[[dict[str, Any]], str]:
    if contexts is None:
        raise ValueError("inspect_context requires contexts")
    index = {c.meta.id: c for c in contexts}
    return lambda inp: execute(inp, index)
