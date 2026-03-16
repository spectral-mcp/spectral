"""Token usage tracking and cost estimation."""

from __future__ import annotations

from typing import Any

from cli.helpers.console import console

_total_input_tokens: int = 0
_total_output_tokens: int = 0
_total_cache_read_tokens: int = 0
_total_cache_creation_tokens: int = 0
_total_cost: float = 0.0


def record_usage(usage: Any, label: str) -> None:
    """Accumulate token counts from a PydanticAI ``RunUsage`` and print a dim summary."""
    global _total_input_tokens, _total_output_tokens
    global _total_cache_read_tokens, _total_cache_creation_tokens, _total_cost

    if usage is None:
        return

    inp = int(getattr(usage, "input_tokens", 0) or 0)
    out = int(getattr(usage, "output_tokens", 0) or 0)
    _total_input_tokens += inp
    _total_output_tokens += out

    cache_read = int(getattr(usage, "cache_read_tokens", 0) or 0)
    cache_create = int(getattr(usage, "cache_write_tokens", 0) or 0)
    _total_cache_read_tokens += cache_read
    _total_cache_creation_tokens += cache_create

    call_cost = _estimate_cost(inp, out, cache_read, cache_create)
    if call_cost is not None:
        _total_cost += call_cost

    if label:
        line = f"  [dim]{label:<30} {inp:,} in · {out:,} out"
        if cache_read or cache_create:
            cache_parts: list[str] = []
            if cache_read:
                cache_parts.append(f"{cache_read:,} read")
            if cache_create:
                cache_parts.append(f"{cache_create:,} write")
            line += f" (cache: {', '.join(cache_parts)})"
        if call_cost is not None:
            line += f" · ${call_cost:.4f}"
        line += "[/dim]"
        console.print(line)


def reset_usage() -> None:
    """Reset all token counters to zero."""
    global _total_input_tokens, _total_output_tokens
    global _total_cache_read_tokens, _total_cache_creation_tokens, _total_cost
    _total_input_tokens = 0
    _total_output_tokens = 0
    _total_cache_read_tokens = 0
    _total_cache_creation_tokens = 0
    _total_cost = 0.0


def print_usage_summary() -> None:
    """Print a formatted usage summary line."""
    if not (_total_input_tokens or _total_output_tokens):
        return
    cost_str = f" (~${_total_cost:.2f})" if _total_cost else ""
    console.print(
        f"  LLM token usage: {_total_input_tokens:,} input, "
        f"{_total_output_tokens:,} output{cost_str}"
    )


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float | None:
    """Return estimated USD cost, or ``None`` if model pricing is unknown."""
    from cli.helpers.llm._client import get_or_create_config

    config = get_or_create_config()
    if config.input_price_per_m is None or config.output_price_per_m is None:
        return None
    inp_rate = config.input_price_per_m
    out_rate = config.output_price_per_m
    return (
        input_tokens * inp_rate
        + cache_read_tokens * inp_rate * 0.1
        + cache_creation_tokens * inp_rate * 1.25
        + output_tokens * out_rate
    ) / 1_000_000
