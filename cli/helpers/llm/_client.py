"""Config resolution.

PydanticAI handles the Anthropic client, retry, and rate limiting internally.
This module provides ``get_or_create_config()`` which returns the stored config
or interactively prompts for one.
"""

from __future__ import annotations

import click

from cli.formats.config import Config
import cli.helpers.llm.providers as providers
import cli.helpers.storage as storage

_config_override: Config | None = None


def set_config(config: Config) -> None:
    """Override the config returned by ``get_or_create_config``."""
    global _config_override
    _config_override = config


def clear_config() -> None:
    """Remove the config override."""
    global _config_override
    _config_override = None


def create_config_interactive(existing: Config | None = None) -> Config:
    """Run the interactive config flow and save to disk."""
    provider = providers.select_provider()

    if provider in ("ollama",):
        key = ""
    elif provider == "openai-compatible":
        key = click.prompt("API key (optional)", default="").strip()
    else:
        default_key = (
            existing.api_key if existing and existing.provider == provider else ""
        )
        key = click.prompt("API key", default=default_key, hide_input=True).strip()

    providers.validate_api_key(provider, key)

    if provider == "openai-compatible":
        default_url = (
            existing.base_url
            if existing
            and existing.provider == "openai-compatible"
            and existing.base_url
            else ""
        )
        base_url: str | None = click.prompt("Base URL", default=default_url).strip()
    else:
        base_url = providers.resolve_base_url(provider)

    model, inp_price, out_price = providers.select_model_interactive(
        provider, api_key=key
    )

    config = Config(
        api_key=key,
        model=model,
        provider=provider,
        base_url=base_url,
        input_price_per_m=inp_price or None,
        output_price_per_m=out_price or None,
    )
    storage.write_config(config)
    return config


def current_model() -> str:
    """Return the model name from the active config."""
    return get_or_create_config().model


def get_or_create_config() -> Config:
    """Return config from override, disk, or create it interactively."""
    if _config_override is not None:
        return _config_override

    config = storage.load_config()
    if config:
        return config

    click.echo(
        "\nTo use this command, Spectral needs an API key.\n"
        f"\nThe config will be saved to {storage.config_path()}\n"
    )

    return create_config_interactive()
