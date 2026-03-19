"""CLI command: spectral android uninstall."""

from __future__ import annotations

import click

from cli.helpers.console import console


@click.command()
@click.argument("package")
def uninstall(package: str) -> None:
    """Uninstall a package from a connected Android device."""
    from cli.commands.android.external_tools.adb import check_adb, uninstall_app

    check_adb()

    console.print(f"[bold]Uninstalling:[/bold] {package}")
    uninstall_app(package)
    console.print("[green]Uninstall successful[/green]")
