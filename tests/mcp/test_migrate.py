"""Tests for the mcp migrate command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from click.testing import CliRunner
import pytest

from cli.commands.mcp.migrate import migrate
from cli.helpers.storage import app_dir, list_tools, tools_dir


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("SPECTRAL_HOME", str(tmp_path))
    return tmp_path


def _write_app(root: Path, name: str, meta: dict[str, Any]) -> None:
    d = root / "apps" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "app.json").write_text(json.dumps(meta))


def _write_tool(root: Path, app_name: str, tool: dict[str, Any]) -> None:
    td = root / "apps" / app_name / "tools"
    td.mkdir(parents=True, exist_ok=True)
    (td / f"{tool['name']}.json").write_text(json.dumps(tool))


class TestMigrate:
    def test_migrate_converts_path_to_url(self, storage: Path) -> None:
        _write_app(storage, "myapp", {
            "name": "myapp",
            "display_name": "My App",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "base_url": "https://api.example.com",
        })
        _write_tool(storage, "myapp", {
            "name": "get_users",
            "description": "Get users",
            "parameters": {"type": "object", "properties": {}},
            "request": {"method": "GET", "path": "/api/users"},
        })

        result = CliRunner().invoke(migrate)
        assert result.exit_code == 0
        assert "1 tools migrated" in result.output
        assert "1 apps updated" in result.output

        # Verify app.json was migrated
        from cli.formats.app_meta import AppMeta

        meta = AppMeta.model_validate_json(
            (app_dir("myapp") / "app.json").read_text()
        )
        assert meta.base_urls == ["https://api.example.com"]

        # Verify tool was migrated
        tools = list_tools("myapp")
        assert len(tools) == 1
        assert tools[0].request.url == "https://api.example.com/api/users"

    def test_migrate_strips_unused_params(self, storage: Path) -> None:
        _write_app(storage, "myapp", {
            "name": "myapp",
            "display_name": "My App",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "base_urls": ["https://api.example.com"],
        })
        _write_tool(storage, "myapp", {
            "name": "get_user",
            "description": "Get a user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "unused_param": {"type": "string"},
                },
                "required": ["user_id", "unused_param"],
            },
            "request": {
                "method": "GET",
                "url": "https://api.example.com/api/users/{user_id}",
            },
        })

        result = CliRunner().invoke(migrate)
        assert result.exit_code == 0
        assert "1 tools migrated" in result.output

        tools = list_tools("myapp")
        assert len(tools) == 1
        props = tools[0].parameters["properties"]
        assert "user_id" in props
        assert "unused_param" not in props
        assert tools[0].parameters.get("required") == ["user_id"]

    def test_migrate_deletes_unfixable_tool(self, storage: Path) -> None:
        _write_app(storage, "myapp", {
            "name": "myapp",
            "display_name": "My App",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "base_urls": ["https://api.example.com"],
        })
        # Tool with path but also a URL param that won't resolve
        _write_tool(storage, "myapp", {
            "name": "broken_tool",
            "description": "Broken",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                },
                "required": ["id"],
            },
            "request": {
                "method": "GET",
                "path": "/api/{missing_param}",
                "body": {"val": {"$param": "id"}},
            },
        })

        result = CliRunner().invoke(migrate)
        assert result.exit_code == 0
        assert "1 tools removed" in result.output

        td = tools_dir("myapp")
        assert not (td / "broken_tool.json").exists()
