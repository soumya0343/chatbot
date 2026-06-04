from __future__ import annotations

import logging
import os
from typing import AsyncIterator

from openai import AsyncOpenAI

from .base import BaseProvider
from ..models import ChatMessage, ProviderMeta, StreamChunk

logger = logging.getLogger(__name__)

# Groq exposes an OpenAI-compatible Chat Completions API, so we reuse the
# openai SDK with a base_url override instead of adding a new dependency.
GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(BaseProvider):
    def __init__(self, api_key: str | None = None):
        self._client = AsyncOpenAI(
            api_key=api_key or os.environ.get("GROQ_API_KEY", ""),
            base_url=GROQ_BASE_URL,
        )

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> tuple[str, ProviderMeta]:
        response = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        text = response.choices[0].message.content or ""
        meta = ProviderMeta(
            request_id=response.id,
            input_tokens=response.usage.prompt_tokens if response.usage else None,
            output_tokens=response.usage.completion_tokens if response.usage else None,
        )
        return text, meta

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> AsyncIterator[tuple[StreamChunk, ProviderMeta]]:
        stream = await self._client.chat.completions.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            stream=True,
            stream_options={"include_usage": True},
        )
        request_id: str | None = None
        saw_final = False

        async for chunk in stream:
            if request_id is None:
                request_id = chunk.id

            if chunk.usage:
                # Emitted in the final chunk when Groq honors include_usage.
                saw_final = True
                yield StreamChunk(text="", is_final=True), ProviderMeta(
                    request_id=request_id,
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                )
            elif chunk.choices and chunk.choices[0].delta.content:
                yield StreamChunk(text=chunk.choices[0].delta.content), ProviderMeta()

        if not saw_final:
            # Fallback: still emit a final sentinel so TrackedClient.stream() and
            # the Redis event path behave as usual even without a usage chunk.
            yield StreamChunk(text="", is_final=True), ProviderMeta(request_id=request_id)
