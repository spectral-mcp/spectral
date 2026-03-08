"""Shell completion script generator."""

from __future__ import annotations

import click


@click.command()
@click.argument("shell", type=click.Choice(["bash", "zsh"]))
def completion(shell: str) -> None:
    """Generate shell completion script.

    Print the completion script for the given shell to stdout.
    Add it to your shell profile to enable tab-completion:

    \b
        eval "$(spectral completion bash)"   # bash
        eval "$(spectral completion zsh)"     # zsh
    """
    from click.shell_completion import BashComplete, ZshComplete

    from cli.main import cli as root_cli

    cls = BashComplete if shell == "bash" else ZshComplete
    comp = cls(root_cli, {}, "spectral", "_SPECTRAL_COMPLETE")
    click.echo(comp.source())
