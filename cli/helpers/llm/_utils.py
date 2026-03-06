"""Small utility functions shared across the LLM sub-modules."""

from __future__ import annotations

from typing import Any


def extract_text(content: list[Any]) -> str:
    """Join all text blocks from an LLM response content list."""
    return "\n".join(
        block.text for block in content if getattr(block, "type", None) == "text"
    )
