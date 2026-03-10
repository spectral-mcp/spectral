"""Anthropic client lifecycle and transport layer (retry, semaphore, rate limiting)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import click

from cli.helpers.console import console
import cli.helpers.storage as storage

_client: Any = None
_semaphore: asyncio.Semaphore | None = None

MAX_CONCURRENT = 5
MAX_RETRIES = 3
FALLBACK_BACKOFF = 2.0  # seconds, doubled each retry


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

    import anthropic

    _client = anthropic.AsyncAnthropic(api_key=key)


def clear_client() -> None:
    """Clear the module-level client and semaphore."""
    global _client, _semaphore
    _client = None
    _semaphore = None


def _get_semaphore() -> asyncio.Semaphore:
    """Return the module-level semaphore, lazily creating it."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    return _semaphore


def _parse_retry_after(exc: Exception) -> float | None:
    """Extract ``retry-after`` seconds from an Anthropic error response."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


async def send(*, label: str = "", **kwargs: Any) -> Any:
    """Call ``client.messages.create`` with semaphore gating and rate-limit retry."""
    import anthropic

    from cli.helpers.llm._cost import record_usage

    semaphore = _get_semaphore()
    delay = FALLBACK_BACKOFF

    async with semaphore:
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await get_client().messages.create(**kwargs)
                record_usage(response, label, kwargs.get("model", ""))
                return response
            except anthropic.RateLimitError as exc:
                if attempt >= MAX_RETRIES:
                    tag = f" ({label})" if label else ""
                    console.print(
                        f"  [red]Rate limit exceeded{tag}, "
                        f"giving up after {MAX_RETRIES} retries[/red]"
                    )
                    raise

                wait = _parse_retry_after(exc)
                if wait is None:
                    wait = delay
                    delay *= 2

                tag = f" ({label})" if label else ""
                console.print(
                    f"  [yellow]Rate limited{tag}, "
                    f"retrying in {wait:.1f}s...[/yellow]"
                )
                await asyncio.sleep(wait)

    raise RuntimeError("unreachable")  # pragma: no cover
