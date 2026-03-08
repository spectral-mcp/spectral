"""CLI command: spectral auth set."""

from __future__ import annotations

import click

from cli.helpers.completions import complete_app_name
from cli.helpers.console import console


@click.command("set")
@click.argument("app_name", shell_complete=complete_app_name)
@click.option("--header", "-H", multiple=True, help='Header as "Name: Value" (repeatable)')
@click.option("--cookie", "-c", multiple=True, help='Cookie as "name=value" (repeatable)')
def set_token(app_name: str, header: tuple[str, ...], cookie: tuple[str, ...]) -> None:
    """Manually set auth headers/cookies for an app.

    Fallback when the generated auth script doesn't work.
    """
    import time

    from cli.formats.mcp_tool import TokenState
    from cli.helpers.storage import resolve_app, write_token

    resolve_app(app_name)

    headers: dict[str, str] = {}

    for h in header:
        if ": " not in h:
            raise click.ClickException(
                f"Invalid header format: {h!r}. Expected 'Name: Value'."
            )
        name, value = h.split(": ", 1)
        headers[name] = value

    if cookie:
        headers["Cookie"] = "; ".join(cookie)

    if not headers:
        token = click.prompt("Token")
        if token.startswith("Bearer "):
            token = token[len("Bearer "):]
        headers["Authorization"] = f"Bearer {token}"

    token_state = TokenState(headers=headers, obtained_at=time.time())
    write_token(app_name, token_state)
    console.print("[green]Token saved.[/green]")
