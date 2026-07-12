"""Shared Pydantic models for API requests/responses and internal agent state."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ToolName(str, Enum):
    SEARCH_DOCUMENTS = "search_documents"
    QUERY_ORDERS = "query_orders"


class Citation(BaseModel):
    source: str
    section: str
    text: str
    score: float


class SqlToolResult(BaseModel):
    query: str
    row_count: int
    rows: list[dict[str, Any]]
    error: str | None = None


class RagToolResult(BaseModel):
    query: str
    citations: list[Citation]


class ToolInvocation(BaseModel):
    tool: ToolName
    result: RagToolResult | SqlToolResult


class ChatMeta(BaseModel):
    """Sent once, before the answer starts streaming, so the UI can render
    tool badges / citations / SQL alongside the (still in-flight) answer."""

    tools_used: list[ToolName]
    citations: list[Citation] = Field(default_factory=list)
    sql_queries: list[str] = Field(default_factory=list)
