"""JSON truncation helpers for LLM consumption."""

from __future__ import annotations

from typing import Any, cast


def truncate_json(obj: Any, max_keys: int = 10, max_depth: int = 4) -> Any:
    """Truncate a JSON-like object for LLM consumption.

    Limits breadth (max_keys per dict, 3 items per list), depth, and string length.
    """
    return _truncate(obj, max_keys, max_depth, 0)


def _truncate(obj: Any, max_keys: int, max_depth: int, depth: int) -> Any:
    if depth >= max_depth:
        if isinstance(obj, dict):
            d = cast(dict[str, Any], obj)
            return {"_truncated": f"{len(d)} keys"}
        if isinstance(obj, list):
            ls = cast(list[Any], obj)
            return [f"...{len(ls)} items"]
        if isinstance(obj, str) and len(obj) > 200:
            return obj[:200] + "..."
        return obj
    if isinstance(obj, dict):
        d = cast(dict[str, Any], obj)
        all_items = list(d.items())
        items = all_items[:max_keys]
        result = {k: _truncate(v, max_keys, max_depth, depth + 1) for k, v in items}
        if len(all_items) > max_keys:
            result["_truncated"] = f"{len(all_items) - max_keys} more keys"
        return result
    if isinstance(obj, list):
        ls = cast(list[Any], obj)
        truncated = [_truncate(item, max_keys, max_depth, depth + 1) for item in ls[:3]]
        if len(ls) > 3:
            truncated.append(f"...{len(ls) - 3} more items")
        return truncated
    if isinstance(obj, str) and len(obj) > 200:
        return obj[:200] + "..."
    return obj
