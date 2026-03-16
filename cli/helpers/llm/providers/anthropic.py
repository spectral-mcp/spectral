"""Anthropic model catalog and interactive selection."""

from __future__ import annotations

from typing import Any

import click
import requests

from cli.helpers.console import console
from cli.helpers.ui import Choice

ANTHROPIC_API_BASE = "https://api.anthropic.com"

# Known per-million-token pricing by model family: (input_$/M, output_$/M).
# Matched by prefix (longest first) — the API does not expose pricing.
_FAMILY_PRICING: list[tuple[str, tuple[float, float]]] = [
    ("claude-opus-4-6", (5.0, 25.0)),
    ("claude-opus-4-5", (5.0, 25.0)),
    ("claude-opus-4-1", (15.0, 75.0)),
    ("claude-opus-4", (15.0, 75.0)),
    ("claude-sonnet-4-6", (3.0, 15.0)),
    ("claude-sonnet-4-5", (3.0, 15.0)),
    ("claude-sonnet-4", (3.0, 15.0)),
    ("claude-haiku-4-5", (1.0, 5.0)),
    ("claude-3-7-sonnet", (3.0, 15.0)),
    ("claude-3-5-sonnet", (3.0, 15.0)),
    ("claude-3-5-haiku", (0.80, 4.0)),
    ("claude-3-opus", (15.0, 75.0)),
    ("claude-3-haiku", (0.25, 1.25)),
]

_ModelChoice = Choice[tuple[str, float, float]]


def _lookup_pricing(model_id: str) -> tuple[float, float]:
    """Return pricing for a model ID using prefix matching."""
    for prefix, pricing in _FAMILY_PRICING:
        if model_id.startswith(prefix):
            return pricing
    return (0.0, 0.0)


def fetch_models(api_key: str) -> list[dict[str, Any]]:
    """Fetch available models from the Anthropic API.

    Returns model dicts with ``id`` and ``display_name``, most recent first.
    """
    resp = requests.get(
        f"{ANTHROPIC_API_BASE}/v1/models",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        params={"limit": 1000},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def list_model_choices(api_key: str) -> list[_ModelChoice]:
    """Fetch models and return choices for the interactive selector."""
    console.print("\n[dim]Fetching models from Anthropic…[/dim]")
    models = fetch_models(api_key)
    if not models:
        raise click.ClickException("No models returned by Anthropic.")

    choices: list[_ModelChoice] = []
    for m in models:
        mid: str = m["id"]
        inp, out = _lookup_pricing(mid)
        columns = [f"${inp:.2f} in", f"${out:.2f} out"] if inp else []
        choices.append(Choice(value=(mid, inp, out), label=mid, columns=columns))
    return choices
