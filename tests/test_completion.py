"""Tests for shell completion helpers and the completion command."""

from __future__ import annotations

from unittest.mock import patch

from click.shell_completion import CompletionItem
from click.testing import CliRunner

from cli.helpers.completions import complete_app_name
from cli.main import cli


def _make_app(name: str, display_name: str = "") -> object:
    """Create a minimal object with name and display_name attributes."""
    from cli.formats.app_meta import AppMeta

    return AppMeta(
        name=name,
        display_name=display_name,
        created_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )


class TestCompleteAppName:
    def test_returns_matching_apps(self) -> None:
        apps = [_make_app("tado", "Tado"), _make_app("twitter", "Twitter"), _make_app("slack", "Slack")]
        with patch("cli.helpers.storage.list_apps", return_value=apps):
            result = complete_app_name(None, None, "t")
        assert len(result) == 2
        assert all(isinstance(r, CompletionItem) for r in result)
        names = [r.value for r in result]
        assert "tado" in names
        assert "twitter" in names

    def test_returns_all_on_empty_prefix(self) -> None:
        apps = [_make_app("a"), _make_app("b")]
        with patch("cli.helpers.storage.list_apps", return_value=apps):
            result = complete_app_name(None, None, "")
        assert len(result) == 2

    def test_returns_empty_on_no_match(self) -> None:
        apps = [_make_app("tado")]
        with patch("cli.helpers.storage.list_apps", return_value=apps):
            result = complete_app_name(None, None, "z")
        assert result == []

    def test_returns_empty_on_exception(self) -> None:
        with patch("cli.helpers.storage.list_apps", side_effect=Exception("boom")):
            result = complete_app_name(None, None, "")
        assert result == []

    def test_includes_display_name_as_help(self) -> None:
        apps = [_make_app("tado", "Tado Home")]
        with patch("cli.helpers.storage.list_apps", return_value=apps):
            result = complete_app_name(None, None, "")
        assert result[0].help == "Tado Home"


class TestCompletionCommand:
    def test_bash_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "bash"])
        assert result.exit_code == 0
        assert "_SPECTRAL_COMPLETE" in result.output

    def test_zsh_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "#compdef" in result.output

    def test_invalid_shell(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "fish"])
        assert result.exit_code != 0
