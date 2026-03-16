"""OpenAI model catalog and interactive selection."""

from __future__ import annotations

from cli.helpers.ui import Choice

# (id, context_length, input_$/M, output_$/M)
_CATALOG: list[tuple[str, int, float, float]] = [
    ("gpt-4o",      128_000,  2.50, 10.0),
    ("gpt-4o-mini", 128_000,  0.15,  0.60),
    ("o3",          200_000, 10.0,  40.0),
    ("o3-mini",     200_000,  1.10,  4.40),
    ("o4-mini",     200_000,  1.10,  4.40),
]

_ModelChoice = Choice[tuple[str, float, float]]


def list_model_choices() -> list[_ModelChoice]:
    """Return choices for the interactive selector."""
    return [
        Choice(
            value=(mid, inp, out),
            label=mid,
            columns=[f"{ctx // 1000}k ctx", f"${inp:.2f} in", f"${out:.2f} out"],
        )
        for mid, ctx, inp, out in _CATALOG
    ]
