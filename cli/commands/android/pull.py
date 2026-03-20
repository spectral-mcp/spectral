"""CLI command: spectral android pull."""

from __future__ import annotations

from pathlib import Path

import click

from cli.helpers.console import console


@click.command()
@click.argument("package")
@click.option(
    "-o",
    "--output",
    default=None,
    help="Output path (.apk file or .apks bundle)",
)
def pull(package: str, output: str | None) -> None:
    """Pull all APKs for a package from a connected Android device.

    Single APK apps are saved as a .apk file. Split APK apps (App Bundles)
    are packed into a .apks zip bundle.
    """
    from cli.commands.android.external_tools.adb import (
        check_adb,
        get_apk_paths,
        pull_apks,
    )

    check_adb()

    console.print(f"[bold]Looking up package:[/bold] {package}")
    apk_paths = get_apk_paths(package)
    is_split = len(apk_paths) > 1

    if is_split:
        console.print(f"  Found {len(apk_paths)} split APKs")
        default_output = Path(f"{package}.apks")
    else:
        console.print("  Found single APK")
        default_output = Path(f"{package}.apk")

    out = Path(output) if output else default_output

    for p in apk_paths:
        console.print(f"  Pulling {p}")

    result_path, _ = pull_apks(package, out)
    console.print(f"[green]Saved to {result_path}[/green]")
