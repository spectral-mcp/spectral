"""Tests for shell completion scripts and the completion command."""

from __future__ import annotations

from click.testing import CliRunner

from cli.main import cli


class TestCompletionCommand:
    def test_bash_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "bash"])
        assert result.exit_code == 0
        assert "_spectral_apps" in result.output
        assert "_spectral" in result.output
        assert "complete -o default" in result.output
        assert "_SPECTRAL_COMPLETE" not in result.output

    def test_zsh_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "#compdef spectral" in result.output
        assert "_spectral_apps" in result.output

    def test_bash_all_groups(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "bash"])
        for group in ("android", "auth", "capture", "completion", "extension", "graphql", "mcp", "openapi"):
            assert group in result.output

    def test_invalid_shell(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["completion", "fish"])
        assert result.exit_code != 0
