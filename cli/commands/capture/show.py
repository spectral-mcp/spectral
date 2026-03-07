"""CLI command: spectral capture show."""

from __future__ import annotations

import click

from cli.helpers.console import console


@click.command()
@click.argument("app_name")
def show(app_name: str) -> None:
    """Show captures for an app."""
    from cli.commands.capture.loader import load_bundle_dir
    from cli.helpers.storage import list_captures, resolve_app

    resolve_app(app_name)
    caps = list_captures(app_name)

    if not caps:
        console.print(f"No captures for app '{app_name}'.")
        return

    console.print(f"[bold]App: {app_name}[/bold]  ({len(caps)} capture(s))\n")

    for i, cap_dir in enumerate(caps, 1):
        bundle = load_bundle_dir(cap_dir)
        m = bundle.manifest
        console.print(f"  [{i}] {cap_dir.name}")
        console.print(f"      Created: {m.created_at}  Method: {m.capture_method}")
        console.print(
            f"      {m.stats.trace_count} traces, "
            f"{m.stats.ws_connection_count} WS conns, "
            f"{m.stats.context_count} contexts"
        )
