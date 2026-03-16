"""Reusable interactive terminal UI helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import sys
from typing import Generic, TypeVar

import click

T = TypeVar("T")


@dataclass
class Choice(Generic[T]):
    """A single option in an interactive selection list."""

    value: T
    label: str
    columns: list[str] = field(default_factory=list)


def select_from_list(choices: list[Choice[T]], message: str = "Select") -> T:
    """Present an interactive fuzzy-search selection and return the chosen value.

    Uses ``questionary`` for arrow-key navigation and type-to-filter.
    Raises ``click.Abort`` if the terminal is not interactive or the user cancels.
    """
    if not sys.stdin.isatty():
        raise click.Abort()

    import questionary

    max_label = max(len(c.label) for c in choices)
    max_cols = max((len(c.columns) for c in choices), default=0)

    # Compute the max width per column position.
    col_widths = [0] * max_cols
    for c in choices:
        for i, col in enumerate(c.columns):
            col_widths[i] = max(col_widths[i], len(col))

    def _format(c: Choice[T]) -> str:
        parts = [f"{c.label:<{max_label}}"]
        for i, col in enumerate(c.columns):
            parts.append(f"{col:>{col_widths[i]}}")
        return "  ".join(parts)

    q_choices = [
        questionary.Choice(title=_format(c), value=c.value) for c in choices
    ]

    result = questionary.select(message, choices=q_choices).ask()
    if result is None:
        raise click.Abort()
    return result  # type: ignore[return-value]
