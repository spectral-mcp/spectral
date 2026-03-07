"""CLI command: spectral android list."""

from __future__ import annotations

import click

from cli.helpers.console import console


@click.command("list")
@click.argument("filter", default=None, required=False)
def list_cmd(filter: str | None) -> None:
    """List installed packages on the connected device.

    Optionally filter by a substring, e.g.: spectral android list spotify
    """
    from cli.commands.android.external_tools.adb import check_adb, list_packages

    check_adb()
    packages = list_packages(filter)

    if not packages:
        console.print("[yellow]No packages found.[/yellow]")
        return

    console.print(f"[bold]{len(packages)} packages:[/bold]")
    for pkg in packages:
        console.print(f"  {pkg}")
