"""Tests for LLM investigation tools and the tool_use conversation loop."""
# pyright: reportPrivateUsage=false

import base64
import json
from typing import Any
from unittest.mock import MagicMock

import pytest

import cli.helpers.llm as llm
from cli.helpers.llm._client import setup
from cli.helpers.llm.tools._decode_base64 import execute as execute_decode_base64
from cli.helpers.llm.tools._decode_jwt import execute as execute_decode_jwt
from cli.helpers.llm.tools._decode_url import execute as execute_decode_url
from tests.conftest import make_openai_response

# --- Executor unit tests (sync, no mocks) ---


class TestDecodeBase64:
    def test_simple_text(self):
        encoded = base64.b64encode(b"hello world").decode()
        assert execute_decode_base64(encoded) == "hello world"

    def test_json_payload(self):
        payload = json.dumps({"page": 1, "size": 20})
        encoded = base64.b64encode(payload.encode()).decode()
        result = execute_decode_base64(encoded)
        assert json.loads(result) == {"page": 1, "size": 20}

    def test_urlsafe_variant(self):
        # URL-safe base64 uses - and _ instead of + and /
        data = b"\xfb\xff\xfe"  # produces +//+ in standard, uses -_ in urlsafe
        encoded = base64.urlsafe_b64encode(data).decode()
        assert "-" in encoded or "_" in encoded  # sanity
        result = execute_decode_base64(encoded)
        assert result.startswith("<binary:")

    def test_missing_padding(self):
        encoded = base64.b64encode(b"test").decode().rstrip("=")
        assert execute_decode_base64(encoded) == "test"

    def test_binary_returns_hex(self):
        data = bytes(range(256))
        encoded = base64.b64encode(data).decode()
        result = execute_decode_base64(encoded)
        assert result.startswith("<binary:")
        assert "00010203" in result

    def test_invalid_input(self):
        with pytest.raises(ValueError, match="Cannot base64-decode"):
            execute_decode_base64("!!!not-base64!!!")


class TestDecodeUrl:
    def test_simple(self):
        assert execute_decode_url("hello%20world") == "hello world"

    def test_complex(self):
        assert execute_decode_url("%2Fapi%2Fdata%3Fq%3D1") == "/api/data?q=1"

    def test_already_decoded(self):
        assert execute_decode_url("already decoded") == "already decoded"


class TestDecodeJwt:
    def test_valid_jwt(self):
        header = (
            base64.urlsafe_b64encode(
                json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
            )
            .decode()
            .rstrip("=")
        )
        payload = (
            base64.urlsafe_b64encode(
                json.dumps({"sub": "1234", "name": "Test"}).encode()
            )
            .decode()
            .rstrip("=")
        )
        token = f"{header}.{payload}.fakesignature"

        result = execute_decode_jwt(token)
        decoded = json.loads(result)
        assert decoded["header"]["alg"] == "HS256"
        assert decoded["payload"]["sub"] == "1234"

    def test_invalid_jwt(self):
        with pytest.raises(ValueError, match="expected at least 2"):
            execute_decode_jwt("not-a-jwt")


# --- Conversation tool-use tests (async, mocked client) ---


def _make_tool_call_response(
    tool_name: str, tool_input: dict[str, Any], tool_call_id: str = "tool_01"
) -> MagicMock:
    """Create a mock OpenAI-style response with a tool_call."""
    import json as _json

    resp = MagicMock()
    tc = MagicMock()
    tc.id = tool_call_id
    tc.function.name = tool_name
    tc.function.arguments = _json.dumps(tool_input)
    message = MagicMock()
    message.content = None
    message.tool_calls = [tc]
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "tool_calls"
    resp.choices = [choice]
    return resp


class TestCallWithTools:
    @pytest.mark.asyncio
    async def test_direct_response_no_tool_use(self):
        """When the LLM responds without tool_use, return text directly."""
        call_count = [0]

        async def mock_send(**kwargs: Any) -> MagicMock:
            call_count[0] += 1
            return make_openai_response('{"endpoints": []}')

        setup(send_fn=mock_send)

        conv = llm.Conversation(
            tool_names=["decode_base64", "decode_url", "decode_jwt"],
        )
        result = await conv.ask_text("hi")
        assert result == '{"endpoints": []}'
        assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_one_tool_round_then_response(self):
        """LLM calls decode_base64, gets result, then responds with text."""
        encoded = base64.b64encode(b'{"page":1}').decode()
        tool_resp = _make_tool_call_response("decode_base64", {"value": encoded})
        final_resp = make_openai_response(
            '[{"method":"GET","pattern":"/api/data/{param}","urls":[]}]'
        )

        call_count = [0]

        async def mock_send(**kwargs: Any) -> MagicMock:
            call_count[0] += 1
            if call_count[0] == 1:
                return tool_resp
            return final_resp

        setup(send_fn=mock_send)

        conv = llm.Conversation(
            tool_names=["decode_base64", "decode_url", "decode_jwt"],
        )
        result = await conv.ask_text("analyze")
        assert "/api/data/{param}" in result
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_executor_error_returned_as_is_error(self):
        """When an executor raises, the error is sent back with is_error=True."""
        tool_resp = _make_tool_call_response(
            "decode_base64", {"value": "!!!not~base64$$$"}
        )
        final_resp = make_openai_response("[]")

        call_count = [0]

        async def mock_send(**kwargs: Any) -> MagicMock:
            call_count[0] += 1
            if call_count[0] == 1:
                return tool_resp
            # Verify the tool_result has is_error — now tool results are individual messages
            messages = kwargs["messages"]
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            assert any(m.get("is_error") for m in tool_msgs)
            return final_resp

        setup(send_fn=mock_send)

        conv = llm.Conversation(
            tool_names=["decode_base64", "decode_url", "decode_jwt"],
        )
        result = await conv.ask_text("go")
        assert result == "[]"

    @pytest.mark.asyncio
    async def test_max_iterations_raises(self):
        """If the LLM keeps calling tools beyond max_iterations, raise ValueError."""
        tool_resp = _make_tool_call_response("decode_url", {"value": "%20"})

        async def mock_send(**kwargs: Any) -> MagicMock:
            return tool_resp

        setup(send_fn=mock_send)

        conv = llm.Conversation(
            tool_names=["decode_base64", "decode_url", "decode_jwt"],
            max_iterations=3,
        )
        with pytest.raises(ValueError, match="exceeded 3 iterations"):
            await conv.ask_text("go")

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        """If the LLM calls a tool not in executors, return an error result."""
        tool_resp = _make_tool_call_response("nonexistent_tool", {"x": 1})
        final_resp = make_openai_response("done")

        call_count = [0]

        async def mock_send(**kwargs: Any) -> MagicMock:
            call_count[0] += 1
            if call_count[0] == 1:
                return tool_resp
            messages = kwargs["messages"]
            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            assert any("Unknown tool" in m.get("content", "") for m in tool_msgs)
            assert any(m.get("is_error") for m in tool_msgs)
            return final_resp

        setup(send_fn=mock_send)

        conv = llm.Conversation(
            tool_names=["decode_base64", "decode_url", "decode_jwt"],
        )
        result = await conv.ask_text("go")
        assert result == "done"
