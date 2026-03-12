"""Internal dataclasses and Pydantic response models for MCP pipeline steps."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from cli.formats.mcp_tool import ToolDefinition


class IdentifyResponse(BaseModel):
    """LLM response for the identify capabilities step."""

    useful: bool
    name: str | None = None
    description: str | None = None


class BuildToolResponse(BaseModel):
    """LLM response for the build tool step."""

    tool: ToolDefinition
    consumed_trace_ids: list[str]


@dataclass
class ToolCandidate:
    """A proposed tool before full definition is built."""

    name: str
    description: str
    trace_ids: list[str]
