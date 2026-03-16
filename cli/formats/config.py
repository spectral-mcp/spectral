"""Spectral configuration model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

Provider = Literal["anthropic", "openrouter", "openai", "ollama", "openai-compatible", "test"]


class Config(BaseModel):
    api_key: str = ""
    model: str = _DEFAULT_MODEL
    provider: Provider = "anthropic"
    base_url: str | None = None
    input_price_per_m: float | None = None
    output_price_per_m: float | None = None
