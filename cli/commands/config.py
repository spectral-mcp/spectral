"""CLI command: spectral config."""

from __future__ import annotations

import click

from cli.helpers.console import console
from cli.helpers.llm import create_config_interactive
from cli.helpers.storage import config_path, load_config


@click.command()
def config() -> None:
    """Configure API key and model."""

    existing = load_config()

    click.echo(f"\nSpectral configuration\nConfig file: {config_path()}\n")

    if existing:
        console.print(f"  Current provider: {existing.provider}")
        if existing.api_key:
            console.print(f"  Current API key:  {existing.api_key[:12]}...")
        console.print(f"  Current model:    {existing.model}\n")

    create_config_interactive(existing)
    console.print(f"\n[green]Config saved to {config_path()}[/green]")
