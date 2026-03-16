"""Test provider — allows injecting a PydanticAI FunctionModel as a regular provider.

Usage in tests::

    from cli.helpers.llm.providers.testing import set_test_model, clear_test_model

    set_test_model(FunctionModel(my_fn))
    # ... Conversation() works without real API key or config ...
    clear_test_model()
"""

from __future__ import annotations

from typing import Any

from cli.formats.config import Config
import cli.helpers.llm._client as _client

_model: Any | None = None


def set_test_model(model: Any) -> None:
    """Register a test model and inject a dummy config so no interactive prompt fires."""
    global _model
    _model = model
    _client.set_config(Config(provider="test"))


def clear_test_model() -> None:
    """Remove the test model and config override."""
    global _model
    _model = None
    _client.clear_config()


def build_model() -> tuple[Any, None]:
    """Return the currently registered test model."""
    if _model is None:
        raise RuntimeError("No test model set — call set_test_model() first.")
    return _model, None
