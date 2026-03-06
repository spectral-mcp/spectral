"""Core conversation engine: Conversation class, tool loop, response model parsing."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
import json
from typing import Any, TypeVar, cast

import anthropic
from pydantic import BaseModel, ValidationError

from cli.commands.capture.types import CaptureBundle
from cli.helpers.console import console
from cli.helpers.json import extract_json
from cli.helpers.llm._client import get_client
from cli.helpers.llm._cost import record_usage
from cli.helpers.llm._debug import DebugSession
from cli.helpers.llm._utils import extract_text
from cli.helpers.llm.tools import execute_tool, make_tools

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
MAX_CONCURRENT = 5
MAX_RETRIES = 3
FALLBACK_BACKOFF = 2.0  # seconds, doubled each retry

_semaphore: asyncio.Semaphore | None = None
_model_override: str | None = None

T = TypeVar("T", bound=BaseModel)


def set_model(model: str) -> None:
    """Override the default model for all new conversations."""
    global _model_override
    _model_override = model


def _get_semaphore() -> asyncio.Semaphore:
    """Return the module-level semaphore, lazily creating it."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    return _semaphore


# ---------------------------------------------------------------------------
# Pure utility functions (module-level)
# ---------------------------------------------------------------------------


def _build_system_blocks(
    system: str | list[str] | None,
) -> list[dict[str, Any]] | None:
    """Convert *system* into a list of text blocks with ``cache_control``."""
    if system is None:
        return None
    _CACHE_EPHEMERAL: dict[str, str] = {"type": "ephemeral"}
    if isinstance(system, str):
        return [{"type": "text", "text": system, "cache_control": _CACHE_EPHEMERAL}]
    if len(system) == 1:
        return [{"type": "text", "text": system[0], "cache_control": _CACHE_EPHEMERAL}]
    return [
        {"type": "text", "text": system[0], "cache_control": _CACHE_EPHEMERAL},
        {"type": "text", "text": "\n\n".join(system[1:]), "cache_control": _CACHE_EPHEMERAL},
    ]


def _check_truncation(
    response: Any, *, max_tokens: int, label: str
) -> None:
    """Raise if the response was truncated due to max_tokens."""
    if getattr(response, "stop_reason", None) == "max_tokens":
        tag = f" ({label})" if label else ""
        raise ValueError(
            f"LLM response truncated{tag} (max_tokens={max_tokens}). "
            f"The prompt or expected output is too large."
        )


def _parse_retry_after(exc: Exception) -> float | None:
    """Extract ``retry-after`` seconds from an Anthropic error response."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _try_parse_model(text: str, response_model: type[T]) -> T:
    """Try to parse *text* as JSON and validate against *response_model*."""
    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError:
        data = extract_json(text)
    return response_model.model_validate(data)


# ---------------------------------------------------------------------------
# Conversation class
# ---------------------------------------------------------------------------


class Conversation:
    """A multi-turn conversation with the LLM.

    Config (system, tools, executors, etc.) is fixed at construction.
    ``ask_text(prompt)`` and ``ask_json(prompt, response_model)`` are the
    two public methods.
    """

    def __init__(
        self,
        *,
        system: str | list[str] | None = None,
        tool_names: Sequence[str] | None = None,
        bundle: CaptureBundle | None = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
        max_iterations: int = 10,
        label: str = "",
    ) -> None:
        self._system_blocks = _build_system_blocks(system)
        self._model = _model_override or model
        self._max_tokens = max_tokens
        self._max_iterations = max_iterations
        self._label = label
        self._messages: list[dict[str, Any]] = []
        self._dbg = DebugSession(label or "call")

        if tool_names is not None:
            tools, executors = make_tools(tool_names, bundle)
            if tools:
                tools[-1] = {**tools[-1], "cache_control": {"type": "ephemeral"}}
            self._tools: list[dict[str, Any]] | None = tools
            self._executors: dict[str, Callable[[dict[str, Any]], str]] | None = executors
        else:
            self._tools = None
            self._executors = None

    async def ask_text(self, prompt: str) -> str:
        """Send a user message and return the assistant's text response."""
        self._messages.append({"role": "user", "content": prompt})
        self._dbg.add_user(prompt)

        if self._tools is not None and self._executors is not None:
            text = await self._run_tool_loop()
        else:
            create_kwargs: dict[str, Any] = {}
            if self._system_blocks:
                create_kwargs["system"] = self._system_blocks

            response: Any = await self._send(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=self._messages,
                **create_kwargs,
            )
            text = extract_text(response.content)
            self._dbg.add_assistant(text)
            _check_truncation(response, max_tokens=self._max_tokens, label=self._label)

        self._messages.append({"role": "assistant", "content": text})
        return text

    async def ask_json(self, prompt: str, response_model: type[T]) -> T:
        """Send a user message, parse the response as JSON, and return a validated model.

        Augments *prompt* with a JSON instruction, then retries once on
        parse/validation failure.
        """
        augmented = (
            prompt
            + "\n\nIMPORTANT: Respond with a single minified JSON object. "
            "No commentary, no markdown fences, no explanation — only raw JSON."
        )
        text = await self.ask_text(augmented)

        try:
            return _try_parse_model(text, response_model)
        except (json.JSONDecodeError, ValidationError, ValueError) as first_err:
            parse_error = first_err

        retry_msg = (
            f"Your response could not be parsed: {parse_error}. "
            "Please respond with valid JSON matching the expected schema."
        )
        retry_text = await self.ask_text(retry_msg)
        return _try_parse_model(retry_text, response_model)

    async def _send(self, **kwargs: Any) -> Any:
        """Call ``client.messages.create`` with semaphore gating and rate-limit retry."""
        semaphore = _get_semaphore()
        delay = FALLBACK_BACKOFF
        label = self._label

        async with semaphore:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    response = await get_client().messages.create(**kwargs)
                    record_usage(response, label, kwargs.get("model", ""))
                    return response
                except anthropic.RateLimitError as exc:
                    if attempt >= MAX_RETRIES:
                        tag = f" ({label})" if label else ""
                        console.print(
                            f"  [red]Rate limit exceeded{tag}, "
                            f"giving up after {MAX_RETRIES} retries[/red]"
                        )
                        raise

                    wait = _parse_retry_after(exc)
                    if wait is None:
                        wait = delay
                        delay *= 2

                    tag = f" ({label})" if label else ""
                    console.print(
                        f"  [yellow]Rate limited{tag}, "
                        f"retrying in {wait:.1f}s...[/yellow]"
                    )
                    await asyncio.sleep(wait)

        raise RuntimeError("unreachable")  # pragma: no cover

    async def _run_tool_loop(self) -> str:
        """Call the LLM with tool_use support, looping until a text response."""
        assert self._executors is not None

        _CACHE_EPHEMERAL: dict[str, str] = {"type": "ephemeral"}

        if self._messages and isinstance(self._messages[0].get("content"), str):
            self._messages[0] = {
                **self._messages[0],
                "content": [
                    {
                        "type": "text",
                        "text": self._messages[0]["content"],
                        "cache_control": _CACHE_EPHEMERAL,
                    }
                ],
            }

        create_kwargs: dict[str, Any] = {}
        if self._system_blocks:
            create_kwargs["system"] = self._system_blocks

        for _ in range(self._max_iterations):
            response: Any = await self._send(
                model=self._model,
                max_tokens=self._max_tokens,
                tools=self._tools,
                messages=self._messages,
                **create_kwargs,
            )

            if response.stop_reason == "max_tokens":
                self._dbg.add_assistant(extract_text(response.content) + "\n[TRUNCATED]")
                raise ValueError(
                    f"LLM response truncated ({self._label}, max_tokens={self._max_tokens}). "
                    f"The prompt or expected output is too large."
                )

            if response.stop_reason != "tool_use":
                text = extract_text(response.content)
                self._dbg.add_assistant(text)
                return text

            self._messages.append({"role": "assistant", "content": response.content})
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                if getattr(block, "type", None) == "text" and block.text.strip():
                    self._dbg.add_tool_text(block.text)
                if getattr(block, "type", None) != "tool_use":
                    continue
                tool_result, result_str, is_error = execute_tool(block, self._executors)
                tool_results.append(tool_result)
                self._dbg.add_tool_use(
                    name=block.name, input=block.input, result=result_str, error=is_error,
                )

            for msg in self._messages:
                if msg.get("role") != "user":
                    continue
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for blk in cast(list[dict[str, Any]], content):
                    blk.pop("cache_control", None)

            if tool_results:
                tool_results[-1] = {**tool_results[-1], "cache_control": _CACHE_EPHEMERAL}

            self._messages.append({"role": "user", "content": tool_results})

            self._dbg.flush_tool_round()

        raise ValueError(f"_run_tool_loop exceeded {self._max_iterations} iterations")
