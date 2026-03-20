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
        get_apk_paths,
        install_apk,
        pull_apks,
        uninstall_app,
    )
    from cli.commands.android.patch import patch_apk

    check_adb()

    with tempfile.TemporaryDirectory(prefix="spectral_replace_") as tmpdir:
        tmp = Path(tmpdir)
        is_split = len(get_apk_paths(package)) > 1
        ext = ".apks" if is_split else ".apk"

        console.print(f"[bold]Pulling:[/bold] {package}")
        path, _ = pull_apks(package, tmp / f"original{ext}")

        console.print("[bold]Patching...[/bold]")
        patched = patch_apk(path, tmp / f"patched{ext}")

        console.print(f"[bold]Uninstalling:[/bold] {package}")
        uninstall_app(package)

        console.print("[bold]Installing patched APK...[/bold]")
        install_apk(patched)

    console.print(f"[green]Replaced {package} with patched version[/green]")
