"""Shell completion script generator."""

from __future__ import annotations

import importlib.resources

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
    script = importlib.resources.files("cli.completions").joinpath(f"spectral.{shell}").read_text()
    click.echo(script)
