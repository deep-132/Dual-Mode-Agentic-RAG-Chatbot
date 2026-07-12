"""Tool schemas (as seen by the LLM) and the Python functions that execute them.

Keeping the JSON schema and the executor side by side makes it obvious
when one drifts from the other -- e.g. if a parameter is added to the
schema but never read by the executor.
"""
from __future__ import annotations

from typing import Any

from app.config import Settings
from app.rag.retriever import DocumentRetriever
from app.schemas import RagToolResult, SqlToolResult
from app.sql.db import OrdersRepository

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "Search the company's policy documents (HR leave policy, product FAQ, "
                "returns & refunds policy, warranty policy, pricing & discounts policy) "
                "for text relevant to the user's question. Use this for any question "
                "about policies, rules, procedures, or how something works. "
                "Always cite results returned by this tool; never state policy content "
                "that this tool did not return."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A focused natural-language search query, e.g. 'refund processing time'.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_orders",
            "description": (
                "Run a read-only SQL SELECT query against the `orders` table to answer "
                "questions about specific orders, customers, revenue, order counts, or "
                "order status. Only the `orders` table exists -- never invent other "
                "tables or columns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A single SQLite SELECT statement against the `orders` table.",
                    }
                },
                "required": ["sql"],
            },
        },
    },
]


class ToolExecutor:
    def __init__(self, retriever: DocumentRetriever, orders_repo: OrdersRepository, settings: Settings) -> None:
        self._retriever = retriever
        self._orders_repo = orders_repo
        self._settings = settings

    def run_search_documents(self, query: str) -> RagToolResult:
        citations = self._retriever.search(query, top_k=self._settings.chunk_top_k)
        return RagToolResult(query=query, citations=citations)

    def run_query_orders(self, sql: str) -> SqlToolResult:
        return self._orders_repo.run_query(sql)
