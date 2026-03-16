"""Provider selection and model lookup."""

from __future__ import annotations

from typing import Any

import click

from cli.formats.config import Provider
from cli.helpers.ui import Choice, select_from_list

# Expected key prefix per provider.  ``None`` means any (or empty) key is accepted.
_KEY_PREFIXES: dict[Provider, str | None] = {
    "anthropic": "sk-ant-",
    "openrouter": "sk-or-",
    "openai": "sk-",
    "ollama": None,
    "openai-compatible": None,
    "test": None,
}


def validate_api_key(provider: Provider, api_key: str) -> None:
    """Raise ``click.ClickException`` when the key doesn't match the provider."""
    prefix = _KEY_PREFIXES[provider]
    if prefix is None:
        return  # any key (including empty) is fine
    if not api_key:
        raise click.ClickException(f"{provider} requires an API key.")
    if not api_key.startswith(prefix):
        raise click.ClickException(
            f"{provider} API key should start with '{prefix}'."
        )


def resolve_base_url(provider: Provider) -> str | None:
    """Return the fixed base URL for a provider, or ``None``."""
    if provider == "openrouter":
        from cli.helpers.llm.providers.openrouter import OPENROUTER_API_BASE

        return OPENROUTER_API_BASE
    if provider == "ollama":
        from cli.helpers.llm.providers.ollama import OLLAMA_API_BASE

        return OLLAMA_API_BASE
    return None


def select_provider() -> Provider:
    """Let the user pick a provider interactively."""
    choices: list[Choice[Provider]] = [
        Choice(value="anthropic", label="Anthropic", columns=["Claude models"]),
        Choice(
            value="openrouter",
            label="OpenRouter",
            columns=["Multi-provider gateway"],
        ),
        Choice(value="openai", label="OpenAI", columns=["GPT & o-series models"]),
        Choice(value="ollama", label="Ollama", columns=["Local models"]),
        Choice(
            value="openai-compatible",
            label="OpenAI-compatible",
            columns=["Custom endpoint"],
        ),
    ]
    return select_from_list(choices, message="Provider")


def select_model_interactive(
    provider: Provider, *, api_key: str = ""
) -> tuple[str, float, float]:
    """Let the user pick a model for the given provider.

    Returns ``(model_id, input_price_per_m, output_price_per_m)``.
    """
    if provider == "openai-compatible":
        model = click.prompt("Model name").strip()
        return (model, 0.0, 0.0)

    choices = _list_model_choices(provider, api_key=api_key)
    return select_from_list(choices, message=f"{provider} model")


def _list_model_choices(
    provider: Provider, *, api_key: str
) -> list[Choice[tuple[str, float, float]]]:
    """Dispatch to the provider-specific choice builder."""
    if provider == "anthropic":
        from cli.helpers.llm.providers.anthropic import list_model_choices

        return list_model_choices(api_key)
    if provider == "openrouter":
        from cli.helpers.llm.providers.openrouter import list_model_choices

        return list_model_choices(api_key)
    if provider == "openai":
        from cli.helpers.llm.providers.openai import list_model_choices

        return list_model_choices()
    if provider == "ollama":
        from cli.helpers.llm.providers.ollama import list_model_choices

        return list_model_choices()
    raise ValueError(f"Unknown provider: {provider}")


def build_model(
    provider: Provider,
    *,
    model_name: str,
    api_key: str,
    base_url: str | None,
    max_tokens: int,
) -> tuple[Any, Any]:
    """Build a PydanticAI model + settings for the given provider.

    Returns ``(model, model_settings)`` ready to pass to ``Agent()``.
    """
    if provider == "anthropic":
        return _build_anthropic(model_name, api_key, max_tokens)
    if provider == "test":
        from cli.helpers.llm.providers.testing import build_model as _build_test

        return _build_test()
    return _build_openai(model_name, api_key, base_url, max_tokens)


def _build_anthropic(
    model_name: str, api_key: str, max_tokens: int
) -> tuple[object, object]:
    from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
    from pydantic_ai.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key=api_key)
    model = AnthropicModel(model_name, provider=provider)
    settings = AnthropicModelSettings(
        max_tokens=max_tokens,
        anthropic_cache_instructions="5m",
        anthropic_cache_tool_definitions="5m",
        anthropic_cache_messages="5m",
    )
    return model, settings


def _build_openai(
    model_name: str, api_key: str, base_url: str | None, max_tokens: int
) -> tuple[object, object]:
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider
    from pydantic_ai.settings import ModelSettings

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    provider = OpenAIProvider(**kwargs)
    model = OpenAIChatModel(model_name, provider=provider)
    settings = ModelSettings(max_tokens=max_tokens)
    return model, settings
