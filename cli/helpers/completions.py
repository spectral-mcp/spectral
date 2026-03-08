"""Shell completion helpers for the Spectral CLI."""

from __future__ import annotations

from click.shell_completion import CompletionItem


def complete_app_name(
    ctx: object, param: object, incomplete: str
) -> list[CompletionItem]:
    """Return app names matching *incomplete* for shell completion."""
    try:
        from cli.helpers.storage import list_apps

        return [
            CompletionItem(app.name, help=app.display_name)
            for app in list_apps()
            if app.name.startswith(incomplete)
        ]
    except Exception:
        return []
