from __future__ import annotations

import logging
from typing import AsyncIterator

from anthropic import AsyncAnthropic

from .base import BaseProvider
from ..models import ChatMessage, ProviderMeta, StreamChunk

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str | None = None):
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> tuple[str, ProviderMeta]:
        response = await self._client.messages.create(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        text = response.content[0].text if response.content else ""
        meta = ProviderMeta(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return text, meta

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> AsyncIterator[tuple[StreamChunk, ProviderMeta]]:
        async with self._client.messages.stream(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=kwargs.get("max_tokens", 4096),
        ) as stream:
            async for text in stream.text_stream:
                yield StreamChunk(text=text), ProviderMeta()

            final = await stream.get_final_message()
            request_id = None
            try:
                request_id = stream.response.headers.get("request-id")
            except Exception:
                pass

            yield StreamChunk(text="", is_final=True), ProviderMeta(
                request_id=request_id,
                input_tokens=final.usage.input_tokens,
                output_tokens=final.usage.output_tokens,
            )
