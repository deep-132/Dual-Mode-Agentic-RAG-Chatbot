"""Tests the agentic routing loop in isolation, using a scripted fake LLM
client instead of a real Azure OpenAI deployment -- no network/API key
needed, and each routing scenario (doc-only, sql-only, mixed, no tool) is
fully deterministic."""
from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

from app.agent.orchestrator import FALLBACK_MESSAGE, AgentOrchestrator
from app.config import Settings
from app.schemas import Citation, RagToolResult, SqlToolResult, ToolName


@dataclass
class ScriptedToolCall:
    name: str
    arguments: dict


class FakeLLMClient:
    """Each entry in `script` is either a list of ScriptedToolCall (the model
    wants to call tools) or None (the model is done calling tools)."""

    def __init__(self, script: list[list[ScriptedToolCall] | None], stream_tokens: list[str]):
        self._script = script
        self._stream_tokens = stream_tokens
        self.calls = 0

    def complete(self, messages, tools=None):
        turn = self._script[self.calls]
        self.calls += 1
        if turn is None:
            message = SimpleNamespace(content="final answer", tool_calls=[])
        else:
            tool_calls = [
                SimpleNamespace(
                    id=f"call_{i}",
                    function=SimpleNamespace(name=tc.name, arguments=json.dumps(tc.arguments)),
                )
                for i, tc in enumerate(turn)
            ]
            message = SimpleNamespace(content=None, tool_calls=tool_calls)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    def stream(self, messages):
        yield from self._stream_tokens


class FakeToolExecutor:
    def run_search_documents(self, query: str) -> RagToolResult:
        return RagToolResult(
            query=query,
            citations=[Citation(source="returns_policy.md", section="1. Return Window", text="...", score=0.9)],
        )

    def run_query_orders(self, sql: str) -> SqlToolResult:
        return SqlToolResult(query=sql, row_count=1, rows=[{"order_id": "ORD-1001"}])


def _settings() -> Settings:
    return Settings(max_tool_iterations=4, business_current_date="2026-06-15")


def _run(script, tools_executor=None):
    llm = FakeLLMClient(script, stream_tokens=["Hello", " world"])
    orchestrator = AgentOrchestrator(
        llm=llm, tool_executor=tools_executor or FakeToolExecutor(), settings=_settings(), schema_description="schema"
    )
    events = list(orchestrator.run("some question", history=[]))
    return events, llm


def test_doc_only_question_uses_search_documents_only():
    script = [
        [ScriptedToolCall("search_documents", {"query": "return window"})],
        None,
    ]
    events, llm = _run(script)
    meta = events[0]["data"]
    assert meta.tools_used == [ToolName.SEARCH_DOCUMENTS]
    assert len(meta.citations) == 1
    assert meta.sql_queries == []


def test_data_question_uses_query_orders_only():
    script = [
        [ScriptedToolCall("query_orders", {"sql": "SELECT * FROM orders WHERE status='pending'"})],
        None,
    ]
    events, llm = _run(script)
    meta = events[0]["data"]
    assert meta.tools_used == [ToolName.QUERY_ORDERS]
    assert meta.sql_queries == ["SELECT * FROM orders WHERE status='pending'"]
    assert meta.citations == []


def test_mixed_question_uses_both_tools_in_one_turn():
    script = [
        [
            ScriptedToolCall("search_documents", {"query": "return window"}),
            ScriptedToolCall("query_orders", {"sql": "SELECT * FROM orders WHERE order_id='ORD-1001'"}),
        ],
        None,
    ]
    events, llm = _run(script)
    meta = events[0]["data"]
    assert set(meta.tools_used) == {ToolName.SEARCH_DOCUMENTS, ToolName.QUERY_ORDERS}
    assert len(meta.citations) == 1
    assert len(meta.sql_queries) == 1


def test_out_of_scope_question_calls_no_tools():
    script = [None]
    events, llm = _run(script)
    meta = events[0]["data"]
    assert meta.tools_used == []
    assert meta.citations == []
    assert meta.sql_queries == []


def test_tool_iteration_cap_is_respected():
    # Model keeps requesting tools forever; loop must still terminate and stream an answer.
    endless_tool_calls = [ScriptedToolCall("search_documents", {"query": "x"})]
    script = [endless_tool_calls] * 10
    settings = Settings(max_tool_iterations=3, business_current_date="2026-06-15")
    llm = FakeLLMClient(script, stream_tokens=["ok"])
    orchestrator = AgentOrchestrator(llm=llm, tool_executor=FakeToolExecutor(), settings=settings, schema_description="s")
    events = list(orchestrator.run("q", history=[]))
    assert llm.calls == 3
    assert events[-1]["type"] == "done"


def test_streamed_tokens_are_forwarded_in_order():
    events, _ = _run([None])
    tokens = [e["data"] for e in events if e["type"] == "token"]
    assert tokens == ["Hello", " world"]
    assert events[-1]["type"] == "done"
