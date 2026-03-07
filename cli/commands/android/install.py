"""CLI command: spectral android install."""

from __future__ import annotations

from pathlib import Path

import click

from cli.helpers.console import console


@click.command()
@click.argument("apk_path", type=click.Path(exists=True))
def install(apk_path: str) -> None:
    """Install an APK or directory of split APKs to the device."""
    from cli.commands.android.external_tools.adb import check_adb, install_apk

    check_adb()

    path = Path(apk_path)
    if path.is_dir():
        apks = sorted(path.glob("*.apk"))
        console.print(f"[bold]Installing split APKs:[/bold] {path} ({len(apks)} files)")
    else:
        console.print(f"[bold]Installing APK:[/bold] {path}")

    install_apk(path)
    console.print("[green]Installation successful[/green]")
