"""Anthropic client lifecycle."""

from __future__ import annotations

import os
from typing import Any

import anthropic
import click

import cli.helpers.storage as storage

_client: Any = None


def get_client() -> Any:
    """Return the Anthropic client, lazily initializing if needed."""
    if _client is None:
        setup_client()
    return _client


def setup_client(client: Any = None) -> None:
    """Initialize the Anthropic client (or inject a mock for tests)."""
    global _client

    if client is not None:
        _client = client
        return

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        key = storage.load_api_key()
    if not key:
        click.echo(
            "\nTo use this command, Spectral needs an Anthropic API key.\n"
            "You can create one at https://console.anthropic.com/settings/keys\n"
            f"\nThe key will be saved to {storage.store_root() / 'api_key'}\n"
        )
        key = click.prompt("API key", hide_input=True).strip()
        if not key.startswith("sk-ant-"):
            raise click.ClickException(
                "Invalid API key format (expected a key starting with 'sk-ant-')."
            )
        storage.write_api_key(key)

    _client = anthropic.AsyncAnthropic(api_key=key)


def clear_client() -> None:
    """Clear the module-level client."""
    global _client
    _client = None
