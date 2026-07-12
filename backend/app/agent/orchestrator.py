"""The agentic routing loop.

Two phases per turn, deliberately split:

  Phase 1 (non-streaming): the model sees the tools and decides -- per
  question -- whether to call `search_documents`, `query_orders`, both (in
  either order, including using one call's result to inform the next), or
  neither. This repeats until the model stops requesting tools or a hard
  iteration cap is hit. Streaming has no value here: the payload is JSON
  tool-call arguments, not user-facing prose, so there's nothing worth
  showing token-by-token.

  Phase 2 (streaming): once tool results (if any) are in context, one final
  call generates the natural-language answer, streamed token-by-token to
  the client. Splitting it this way keeps "decide which tools to call" and
  "compose the answer" as two independently testable steps, and lets phase
  1 be fully unit-tested with a fake LLM client that returns canned
  tool_calls -- no streaming mock required.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from app.agent.tools import TOOL_SCHEMAS, ToolExecutor
from app.config import Settings
from app.llm.azure_client import AzureChatClient
from app.schemas import ChatMessage, ChatMeta, Citation, ToolName

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "I don't have that information."

SYSTEM_PROMPT_TEMPLATE = """\
You are the customer support assistant for Northwind Gadgets, a small electronics retailer.

Today's date is {current_date}. Treat this as "now" for any relative date question \
(e.g. "last month", "this year", "in the last 30 days").

You have two tools available:
- search_documents: searches the company's policy documents (returns & refunds, warranty, \
HR leave, product FAQ, pricing & discounts). Use it for any question about policies, rules, \
or procedures.
- query_orders: runs a read-only SQL SELECT against the `orders` table. Use it for any \
question about specific orders, revenue, order counts, customers, or order status.

{schema_description}

Rules:
1. Only state policy facts that a search_documents call actually returned in this \
conversation. Never answer a policy question from memory -- call the tool first.
2. Only state data facts (revenue, counts, order details) that a query_orders call actually \
returned. Never invent column names, tables, or rows.
3. For questions that need both a policy and specific order data (e.g. "did order X qualify \
for the 30-day return window?"), call BOTH tools and combine their results explicitly.
4. If a lookup returns no matching rows (e.g. an order ID that doesn't exist), say so plainly \
-- do not guess or assume it exists.
5. If neither tool can answer the question -- it is out of scope for this company's documents \
and order data -- reply with exactly: "{fallback}" Do not answer from general knowledge.
6. Be concise. When you use a document, name the section you used. When you use order data, \
reference the specific order_id(s) or aggregate you computed.
"""


def _build_system_prompt(settings: Settings, schema_description: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        current_date=settings.business_current_date,
        schema_description=schema_description,
        fallback=FALLBACK_MESSAGE,
    )


def _messages_from_history(history: list[ChatMessage]) -> list[dict[str, Any]]:
    return [{"role": m.role, "content": m.content} for m in history]


class AgentOrchestrator:
    def __init__(
        self,
        llm: AzureChatClient,
        tool_executor: ToolExecutor,
        settings: Settings,
        schema_description: str,
    ) -> None:
        self._llm = llm
        self._tools = tool_executor
        self._settings = settings
        self._system_prompt = _build_system_prompt(settings, schema_description)

    def run(self, user_message: str, history: list[ChatMessage]) -> Iterator[dict[str, Any]]:
        """Yields dicts of shape {"type": "meta"|"token"|"error", "data": ...}.

        This is a plain (synchronous) generator -- Starlette's StreamingResponse
        iterates it in a worker thread, which is exactly right here since the
        Azure OpenAI SDK calls inside are themselves blocking.
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt},
            *_messages_from_history(history),
            {"role": "user", "content": user_message},
        ]

        tools_used: list[ToolName] = []
        citations: list[Citation] = []
        sql_queries: list[str] = []

        for _ in range(self._settings.max_tool_iterations):
            response = self._llm.complete(messages, tools=TOOL_SCHEMAS)
            choice = response.choices[0].message
            tool_calls = choice.tool_calls or []

            if not tool_calls:
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": choice.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tool_call in tool_calls:
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                if name == ToolName.SEARCH_DOCUMENTS.value:
                    result = self._tools.run_search_documents(query=args.get("query", user_message))
                    citations.extend(result.citations)
                    tools_used.append(ToolName.SEARCH_DOCUMENTS)
                    tool_content = result.model_dump_json()
                elif name == ToolName.QUERY_ORDERS.value:
                    result = self._tools.run_query_orders(sql=args.get("sql", ""))
                    if result.error is None:
                        sql_queries.append(result.query)
                    tools_used.append(ToolName.QUERY_ORDERS)
                    tool_content = result.model_dump_json()
                else:
                    tool_content = json.dumps({"error": f"Unknown tool '{name}'"})

                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": tool_content}
                )
        else:
            logger.warning("Tool iteration cap (%s) reached", self._settings.max_tool_iterations)

        meta = ChatMeta(
            tools_used=_dedupe_preserve_order(tools_used),
            citations=_dedupe_citations(citations),
            sql_queries=sql_queries,
        )
        yield {"type": "meta", "data": meta}

        for token in self._llm.stream(messages):
            yield {"type": "token", "data": token}

        yield {"type": "done", "data": None}


def _dedupe_preserve_order(items: list[ToolName]) -> list[ToolName]:
    seen: set[ToolName] = set()
    ordered: list[ToolName] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _dedupe_citations(citations: list[Citation]) -> list[Citation]:
    seen: set[tuple[str, str]] = set()
    ordered: list[Citation] = []
    for c in citations:
        key = (c.source, c.section)
        if key not in seen:
            seen.add(key)
            ordered.append(c)
    return ordered
