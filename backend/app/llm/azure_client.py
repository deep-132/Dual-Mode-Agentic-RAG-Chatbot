"""Thin wrapper around the Azure OpenAI chat completions API.

Kept deliberately dumb (no agent logic here) so the orchestrator can be
unit-tested against a fake client instead of hitting a real deployment.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from openai import AzureOpenAI

from app.config import Settings, require_azure_credentials


class AzureChatClient:
    def __init__(self, settings: Settings) -> None:
        require_azure_credentials(settings)
        self._deployment = settings.azure_openai_chat_deployment
        self._client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Any:
        """Single non-streaming call used for the tool-routing phase, where we
        need the complete tool_calls payload (name + arguments) before we can
        act on it -- there is nothing useful to stream to the user here."""
        return self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,
            tools=tools,
            tool_choice="auto" if tools else None,
            temperature=0,
        )

    def stream(self, messages: list[dict[str, Any]]) -> Iterator[str]:
        """Streaming call for the final natural-language answer, once all tool
        results are already in context. No `tools` param here -- this phase
        only ever produces prose for the user."""
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=messages,
            stream=True,
            temperature=0,
        )
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
