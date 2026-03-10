"""Small utility functions shared across the LLM sub-modules."""

from __future__ import annotations

from typing import Any


def extract_text(response: Any) -> str:
    """Extract text content from an OpenAI-style ChatCompletion response."""
    content = response.choices[0].message.content
    if content is None:
        return ""
    return str(content)
