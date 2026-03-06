"""Tests for the Chrome Native Messaging host -- set_auth handler."""

from __future__ import annotations

import io
import json
import struct

from cli.commands.extension.host import run_host


def _encode_message(msg: dict) -> bytes:
    """Encode a dict as a length-prefixed native messaging message."""
    data = json.dumps(msg).encode("utf-8")
    return struct.pack("<I", len(data)) + data


def _decode_message(raw: bytes) -> dict:
    """Decode a length-prefixed native messaging message."""
    length = struct.unpack("<I", raw[:4])[0]
    return json.loads(raw[4 : 4 + length])


def _run_host_with_message(msg: dict, monkeypatch) -> dict:
    """Feed a message to run_host and return the response."""
    stdin = io.BytesIO(_encode_message(msg))
    stdout = io.BytesIO()
    monkeypatch.setattr("sys.stdin", type("FakeStdin", (), {"buffer": stdin})())
    monkeypatch.setattr("sys.stdout", type("FakeStdout", (), {"buffer": stdout})())
    run_host()
    stdout.seek(0)
    return _decode_message(stdout.read())


class TestSetAuth:
    def test_set_auth_writes_token(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPECTRAL_HOME", str(tmp_path))

        result = _run_host_with_message({
            "type": "set_auth",
            "app_name": "example-com",
            "display_name": "example.com",
            "headers": {
                "Cookie": "session=abc123",
                "Authorization": "Bearer tok",
            },
        }, monkeypatch)

        assert result["success"] is True
        assert result["message"] == "Auth saved"

        # Verify token.json was written
        token_path = tmp_path / "apps" / "example-com" / "token.json"
        assert token_path.exists()
        token_data = json.loads(token_path.read_text())
        assert token_data["headers"]["Cookie"] == "session=abc123"
        assert token_data["headers"]["Authorization"] == "Bearer tok"
        assert "obtained_at" in token_data

    def test_set_auth_creates_app(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPECTRAL_HOME", str(tmp_path))

        _run_host_with_message({
            "type": "set_auth",
            "app_name": "new-app",
            "display_name": "new.app",
            "headers": {"Cookie": "x=1"},
        }, monkeypatch)

        app_json = tmp_path / "apps" / "new-app" / "app.json"
        assert app_json.exists()
        app_data = json.loads(app_json.read_text())
        assert app_data["name"] == "new-app"
        assert app_data["display_name"] == "new.app"

    def test_set_auth_missing_app_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPECTRAL_HOME", str(tmp_path))

        result = _run_host_with_message({
            "type": "set_auth",
            "headers": {"Cookie": "x=1"},
        }, monkeypatch)

        assert result["success"] is False
        assert "Missing" in result["message"]

    def test_set_auth_empty_headers(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPECTRAL_HOME", str(tmp_path))

        result = _run_host_with_message({
            "type": "set_auth",
            "app_name": "test-app",
            "headers": {},
        }, monkeypatch)

        assert result["success"] is False
        assert "Missing" in result["message"]
