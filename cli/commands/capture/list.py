"""CLI command: spectral capture list."""

from __future__ import annotations

import click

from cli.helpers.console import console


@click.command("list")
def list_cmd() -> None:
    """List all known apps with capture counts."""
    from rich.table import Table

    from cli.helpers.storage import list_apps, list_captures

    apps = list_apps()
    if not apps:
        console.print("No apps found. Capture traffic with the Chrome extension or 'spectral capture proxy'.")
        return

    table = Table(title="Apps")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name")
    table.add_column("Captures", justify="right")
    table.add_column("Last Updated")

    for app in apps:
        cap_count = len(list_captures(app.name))
        table.add_row(app.name, app.display_name, str(cap_count), app.updated_at)

    console.print(table)
