"""Ollama local model listing and interactive selection."""

from __future__ import annotations

from typing import Any

import click
import requests

from cli.helpers.console import console
from cli.helpers.ui import Choice

OLLAMA_API_BASE = "http://localhost:11434/v1"

_ModelChoice = Choice[tuple[str, float, float]]


def fetch_models() -> list[dict[str, Any]]:
    """Fetch installed models from the local Ollama instance."""
    resp = requests.get(f"{OLLAMA_API_BASE}/models", timeout=5)
    resp.raise_for_status()
    return resp.json().get("data", [])


def list_model_choices() -> list[_ModelChoice]:
    """Fetch models and return choices for the interactive selector."""
    console.print("\n[dim]Fetching models from Ollama…[/dim]")
    try:
        models = fetch_models()
    except requests.ConnectionError:
        raise click.ClickException(
            "Cannot connect to Ollama at localhost:11434. Is it running?"
        )

    if not models:
        raise click.ClickException("No models installed in Ollama.")

    return [
        Choice(value=(m["id"], 0.0, 0.0), label=m["id"])
        for m in models
    ]
