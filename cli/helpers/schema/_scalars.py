"""Scalar value coercion for schema inference."""

from __future__ import annotations

from typing import Any


def coerce_value(s: str) -> Any:
    """Convert a string value to its natural Python type."""
    if s.isdigit():
        return int(s)
    try:
        return float(s)
    except ValueError:
        pass
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    return s
