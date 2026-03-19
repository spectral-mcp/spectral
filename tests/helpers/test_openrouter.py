"""Tests for provider integration (config, cost, model selection)."""
# pyright: reportPrivateUsage=false, reportUnknownMemberType=false

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest

from cli.formats.config import Config
from cli.helpers.llm._client import clear_config, set_config
from cli.helpers.llm._cost import _estimate_cost
from cli.helpers.llm.providers import validate_api_key

# -- validate_api_key ----------------------------------------------------------


class TestValidateApiKey:
    def test_anthropic_valid(self) -> None:
        validate_api_key("anthropic", "sk-ant-abc123")

    def test_anthropic_empty_raises(self) -> None:
        with pytest.raises(click.ClickException, match="requires an API key"):
            validate_api_key("anthropic", "")

    def test_anthropic_wrong_prefix_raises(self) -> None:
        with pytest.raises(click.ClickException, match="should start with"):
            validate_api_key("anthropic", "sk-or-wrong")

    def test_openrouter_valid(self) -> None:
        validate_api_key("openrouter", "sk-or-abc123")

    def test_openrouter_wrong_prefix_raises(self) -> None:
        with pytest.raises(click.ClickException, match="should start with"):
            validate_api_key("openrouter", "sk-ant-wrong")

    def test_openai_valid(self) -> None:
        validate_api_key("openai", "sk-proj-abc123")

    def test_openai_empty_raises(self) -> None:
        with pytest.raises(click.ClickException, match="requires an API key"):
            validate_api_key("openai", "")

    def test_openai_compatible_empty_ok(self) -> None:
        validate_api_key("openai-compatible", "")

    def test_openai_compatible_any_key_ok(self) -> None:
        validate_api_key("openai-compatible", "anything-goes")


# -- Config model -------------------------------------------------------------


class TestConfigModel:
    def test_defaults(self) -> None:
        cfg = Config(api_key="sk-ant-test")
        assert cfg.provider == "anthropic"
        assert cfg.base_url is None
        assert cfg.input_price_per_m is None
        assert cfg.output_price_per_m is None

    def test_openrouter_config(self) -> None:
        cfg = Config(
            api_key="sk-or-test",
            model="anthropic/claude-sonnet-4-5-20250929",
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
            input_price_per_m=3.0,
            output_price_per_m=15.0,
        )
        assert cfg.provider == "openrouter"
        assert cfg.input_price_per_m == 3.0

    def test_openai_config(self) -> None:
        cfg = Config(
            api_key="sk-test",
            model="gpt-4o",
            provider="openai",
        )
        assert cfg.provider == "openai"

    def test_openai_compatible_config(self) -> None:
        cfg = Config(
            model="my-model",
            provider="openai-compatible",
            base_url="http://localhost:8080/v1",
        )
        assert cfg.provider == "openai-compatible"
        assert cfg.api_key == ""
        assert cfg.base_url == "http://localhost:8080/v1"


# -- Cost estimation ----------------------------------------------------------


class TestCostEstimation:
    def setup_method(self) -> None:
        set_config(Config(
            provider="test",
            input_price_per_m=2.5,
            output_price_per_m=10.0,
        ))

    def teardown_method(self) -> None:
        clear_config()

    def test_estimate_with_pricing(self) -> None:
        cost = _estimate_cost(1_000_000, 1_000_000)
        assert cost is not None
        assert cost == pytest.approx(12.5)

    def test_no_pricing_returns_none(self) -> None:
        set_config(Config(provider="test"))
        assert _estimate_cost(1000, 1000) is None


# -- list_model_choices (mocked) -----------------------------------------------


class TestOpenRouterListModelChoices:
    @patch("cli.helpers.llm.providers.openrouter.console")
    @patch("cli.helpers.llm.providers.openrouter.requests.get")
    def test_returns_choices_with_pricing(
        self,
        mock_get: MagicMock,
        _mock_console: MagicMock,
    ) -> None:
        mock_get.return_value.json.return_value = {
            "data": [
                {
                    "id": "openai/gpt-4o",
                    "name": "GPT-4o",
                    "context_length": 128000,
                    "architecture": {"input_modalities": ["text", "image"]},
                    "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                },
                {
                    "id": "anthropic/claude-sonnet-4-5-20250929",
                    "name": "Claude Sonnet 4.5",
                    "context_length": 200000,
                    "architecture": {"input_modalities": ["text"]},
                    "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                },
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()

        from cli.helpers.llm.providers.openrouter import list_model_choices

        choices = list_model_choices("sk-or-test")

        assert len(choices) == 2
        # Anthropic sorts first
        mid, inp, out = choices[0].value
        assert mid == "anthropic/claude-sonnet-4-5-20250929"
        assert inp == pytest.approx(3.0)
        assert out == pytest.approx(15.0)
        # Then OpenAI
        mid, inp, out = choices[1].value
        assert mid == "openai/gpt-4o"
        assert inp == pytest.approx(2.5)
        assert out == pytest.approx(10.0)
