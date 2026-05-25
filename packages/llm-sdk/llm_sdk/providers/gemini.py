from __future__ import annotations

import logging
import os
from typing import AsyncIterator

import google.generativeai as genai

from .base import BaseProvider
from ..models import ChatMessage, ProviderMeta, StreamChunk

logger = logging.getLogger(__name__)


def _to_gemini_contents(messages: list[ChatMessage]) -> list[dict]:
    """Convert ChatMessage list to Gemini contents format.

    Gemini uses 'user' and 'model' roles (not 'assistant').
    System messages are prepended to the first user message.
    """
    contents = []
    system_parts = []

    for msg in messages:
        if msg.role == "system":
            system_parts.append(msg.content)
        else:
            role = "model" if msg.role == "assistant" else "user"
            text = msg.content
            if system_parts and role == "user" and not contents:
                text = "\n\n".join(system_parts) + "\n\n" + text
                system_parts = []
            contents.append({"role": role, "parts": [{"text": text}]})

    return contents


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str | None = None):
        key = api_key or os.environ.get("GOOGLE_API_KEY", "")
        genai.configure(api_key=key)

    def _model(self, model_name: str) -> genai.GenerativeModel:
        return genai.GenerativeModel(model_name=model_name)

    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> tuple[str, ProviderMeta]:
        contents = _to_gemini_contents(messages)
        response = await self._model(model).generate_content_async(contents)
        text = response.text or ""
        usage = response.usage_metadata
        meta = ProviderMeta(
            input_tokens=usage.prompt_token_count if usage else None,
            output_tokens=usage.candidates_token_count if usage else None,
        )
        return text, meta

    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> AsyncIterator[tuple[StreamChunk, ProviderMeta]]:
        contents = _to_gemini_contents(messages)
        response = await self._model(model).generate_content_async(
            contents, stream=True
        )

        last_usage = None
        async for chunk in response:
            if chunk.usage_metadata and chunk.usage_metadata.candidates_token_count:
                last_usage = chunk.usage_metadata
            if chunk.text:
                yield StreamChunk(text=chunk.text), ProviderMeta()

        yield StreamChunk(text="", is_final=True), ProviderMeta(
            input_tokens=last_usage.prompt_token_count if last_usage else None,
            output_tokens=last_usage.candidates_token_count if last_usage else None,
        )
