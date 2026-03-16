"""OpenRouter model listing and interactive selection."""

from __future__ import annotations

from typing import Any

import click
import requests

from cli.helpers.console import console
from cli.helpers.ui import Choice

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

_PRIORITY_PREFIXES = [
    "anthropic/",
    "openai/",
    "google/",
    "meta-llama/",
    "deepseek/",
    "mistralai/",
    "minimax/",
]

_ModelChoice = Choice[tuple[str, float, float]]


def _sort_key(model_id: str) -> tuple[int, str]:
    """Return a sort key that puts priority providers first."""
    for idx, prefix in enumerate(_PRIORITY_PREFIXES):
        if model_id.startswith(prefix):
            return (idx, model_id)
    return (len(_PRIORITY_PREFIXES), model_id)


def _price_per_million(per_token: str | None) -> float | None:
    """Convert per-token price string to per-million-tokens float."""
    if per_token is None:
        return None
    try:
        return float(per_token) * 1_000_000
    except (ValueError, TypeError):
        return None


def fetch_models(api_key: str) -> list[dict[str, Any]]:
    """Fetch the model list from OpenRouter.

    Returns the raw list of model dicts from the ``/models`` endpoint,
    filtered to text-capable models and sorted with popular providers first.
    """
    resp = requests.get(
        f"{OPENROUTER_API_BASE}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    resp.raise_for_status()
    data: list[dict[str, Any]] = resp.json().get("data", [])

    text_models: list[dict[str, Any]] = [
        m
        for m in data
        if "text" in (m.get("architecture", {}).get("input_modalities") or [])
    ]

    text_models.sort(key=lambda m: _sort_key(m["id"]))
    return text_models


def list_model_choices(api_key: str) -> list[_ModelChoice]:
    """Fetch models and return choices for the interactive selector."""
    console.print("\n[dim]Fetching models from OpenRouter…[/dim]")
    models = fetch_models(api_key)
    if not models:
        raise click.ClickException("No models returned by OpenRouter.")

    choices: list[_ModelChoice] = []
    for m in models:
        pricing: dict[str, Any] = m.get("pricing") or {}
        inp = _price_per_million(pricing.get("prompt")) or 0.0
        out = _price_per_million(pricing.get("completion")) or 0.0
        ctx: int = m.get("context_length") or 0
        choices.append(Choice(
            value=(m["id"], inp, out),
            label=m["id"],
            columns=[
                f"{ctx // 1000}k ctx" if ctx else "",
                f"${inp:.2f} in",
                f"${out:.2f} out",
            ],
        ))
    return choices
