from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from ..models import ChatMessage, ProviderMeta, StreamChunk


class BaseProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> tuple[str, ProviderMeta]:
        """Non-streaming completion. Returns (text, meta)."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        model: str,
        **kwargs,
    ) -> AsyncIterator[tuple[StreamChunk, ProviderMeta]]:
        """Streaming completion.

        Yields (StreamChunk, ProviderMeta) pairs.
        Text chunks have is_final=False and empty ProviderMeta.
        Final sentinel chunk has is_final=True, empty text, and populated ProviderMeta
        (request_id, input_tokens, output_tokens).
        """
        ...
