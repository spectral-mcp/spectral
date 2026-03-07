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
    help="Output path (file for single APK, directory for splits)",
)
def pull(package: str, output: str | None) -> None:
    """Pull all APKs for a package from a connected Android device.

    Single APK apps are saved as a file. Split APK apps (App Bundles)
    are saved as a directory containing all split APKs.
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
        default_output = Path(package)
    else:
        console.print("  Found single APK")
        default_output = Path(f"{package}.apk")

    out = Path(output) if output else default_output

    for p in apk_paths:
        console.print(f"  Pulling {p}")

    result_path, was_split = pull_apks(package, out)

    if was_split:
        apk_files = sorted(result_path.glob("*.apk"))
        console.print(f"[green]Split APKs saved to {result_path}/[/green]")
        for f in apk_files:
            console.print(f"  {f.name}")
    else:
        console.print(f"[green]APK saved to {result_path}[/green]")
