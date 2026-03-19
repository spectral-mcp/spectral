"""CLI command: spectral android replace."""

from __future__ import annotations

from pathlib import Path
import tempfile

import click

from cli.helpers.console import console


@click.command()
@click.argument("package")
def replace(package: str) -> None:
    """Pull, patch, uninstall, and reinstall a package in one step.

    Chains pull → patch → uninstall → install using a temporary directory
    that is cleaned up automatically.
    """
    from cli.commands.android.external_tools.adb import (
        check_adb,
        install_apk,
        pull_apks,
        uninstall_app,
    )
    from cli.commands.android.patch import patch_apk, patch_apk_dir

    check_adb()

    with tempfile.TemporaryDirectory(prefix="spectral_replace_") as tmpdir:
        tmp = Path(tmpdir)

        console.print(f"[bold]Pulling:[/bold] {package}")
        path, is_split = pull_apks(package, tmp / "original")

        console.print("[bold]Patching...[/bold]")
        if is_split:
            patched = patch_apk_dir(path, tmp / "patched")
        else:
            patched = patch_apk(path, tmp / "patched.apk")

        console.print(f"[bold]Uninstalling:[/bold] {package}")
        uninstall_app(package)

        console.print("[bold]Installing patched APK...[/bold]")
        install_apk(patched)

    console.print(f"[green]Replaced {package} with patched version[/green]")
