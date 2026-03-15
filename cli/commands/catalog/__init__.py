"""Community command group — community tool catalog."""

from __future__ import annotations

import click

from cli.commands.catalog.install import install
from cli.commands.catalog.login import login
from cli.commands.catalog.logout import logout
from cli.commands.catalog.publish import publish
from cli.commands.catalog.search import search


@click.group()
def community() -> None:
    """Community tool catalog: publish, search, and install tools."""


community.add_command(install)
community.add_command(login)
community.add_command(logout)
community.add_command(publish)
community.add_command(search)
