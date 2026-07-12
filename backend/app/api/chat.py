"""Chat endpoint: streams Server-Sent Events for a single turn.

Event sequence sent to the client:
  1. `meta`  (once)   -- {tools_used, citations, sql_queries}, so the UI can
                         render the "used RAG / SQL / both" badge and the
                         citation/SQL panel *before* the prose has finished.
  2. `token` (many)   -- {"text": "..."} chunks of the answer, in order.
  3. `done`  (once)   -- turn complete.
  4. `error` (at most once, instead of the above) -- surfaced as text so the
                         UI can show a failure state rather than hang.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


def _sse(event: str, data: dict | None) -> str:
    payload = json.dumps(data if data is not None else {})
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    orchestrator = request.app.state.orchestrator

    def event_stream():
        try:
            for event in orchestrator.run(body.message, body.history):
                if event["type"] == "meta":
                    yield _sse("meta", event["data"].model_dump(mode="json"))
                elif event["type"] == "token":
                    yield _sse("token", {"text": event["data"]})
                elif event["type"] == "done":
                    yield _sse("done", {})
        except Exception:
            logger.exception("Agent run failed")
            yield _sse("error", {"message": "Something went wrong processing your request."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
