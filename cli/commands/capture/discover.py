"""CLI command: spectral capture discover."""

from __future__ import annotations

import click

from cli.helpers.console import console


@click.command()
@click.option("-p", "--port", default=8080, help="Proxy listen port")
def discover(port: int) -> None:
    """Discover domains without intercepting traffic.

    Runs a passthrough proxy that logs TLS SNI hostnames and plain
    HTTP hosts. No MITM — all connections pass through untouched.
    """
    from cli.commands.capture.proxy import run_discover

    console.print(f"[bold]Starting domain discovery on port {port}[/bold]")
    console.print("  No MITM — logging domains only.")
    click.echo("\n  Listening... press Ctrl+C to stop.\n")

    domains = run_discover(port)

    if domains:
        console.print(f"\n  Discovered {len(domains)} domain(s):\n")
        for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
            console.print(f"    {count:4d}  {domain}")
        top = sorted(domains.items(), key=lambda x: -x[1])[0][0]
        console.print("\n  Re-run with -d to capture specific domains, e.g.:")
        console.print(f"    spectral capture proxy -d '{top}'\n")
    else:
        console.print("\n  No domains discovered.\n")
