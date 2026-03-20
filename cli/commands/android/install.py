"""CLI command: spectral android install."""

from __future__ import annotations

from pathlib import Path

import click

from cli.helpers.console import console


@click.command()
@click.argument("apk_path", type=click.Path(exists=True))
def install(apk_path: str) -> None:
    """Install a .apk or .apks bundle to the device."""
    from cli.commands.android.external_tools.adb import check_adb, install_apk

    check_adb()

    path = Path(apk_path)
    console.print(f"[bold]Installing:[/bold] {path}")
    install_apk(path)
    console.print("[green]Installation successful[/green]")
