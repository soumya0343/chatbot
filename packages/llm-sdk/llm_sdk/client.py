from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Literal

from .emitter import emit_event
from .models import ChatMessage, InferenceEvent, StreamChunk
from .pii import truncate_preview
from .providers.anthropic import AnthropicProvider
from .providers.base import BaseProvider
from .providers.gemini import GeminiProvider
from .providers.groq import GroqProvider
from .providers.openai import OpenAIProvider
from .providers.sarvam import SarvamProvider
from .streaming import StreamingTracker

__version__ = "0.1.0"

logger = logging.getLogger(__name__)

PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "sarvam": SarvamProvider,
    "groq": GroqProvider,
}

ProviderName = Literal["anthropic", "openai", "gemini", "sarvam", "groq"]


class TrackedClient:
    """Drop-in LLM wrapper that captures inference metadata and publishes to Redis Streams.

    Usage:
        client = TrackedClient(
            provider="anthropic",
            model="claude-sonnet-4-6",
            session_id="<uuid>",
            redis_client=redis_client,
        )
        # non-streaming
        text = await client.chat(messages)
        # streaming
        async for chunk in client.stream(messages):
            yield chunk.text
    """

    def __init__(
        self,
        provider: ProviderName,
        model: str,
        session_id: str,
        redis_client=None,
        stream_key: str = "llm-inference-logs",
        emit_logs: bool = True,
        metadata: dict | None = None,
    ) -> None:
        if provider not in PROVIDER_REGISTRY:
            raise ValueError(
                f"Unknown provider '{provider}'. Valid: {list(PROVIDER_REGISTRY)}"
            )
        self.provider = provider
        self.model = model
        self.session_id = session_id
        self.redis_client = redis_client
        self.stream_key = stream_key
        self.emit_logs = emit_logs
        self.metadata = metadata or {}
        self._cancelled = False
        self._provider: BaseProvider = PROVIDER_REGISTRY[provider]()

    async def cancel(self) -> None:
        self._cancelled = True

    async def chat(self, messages: list[ChatMessage], **kwargs) -> str:
        started_at = datetime.now(timezone.utc)
        status: str = "success"
        error_code: str | None = None
        error_message: str | None = None
        text = ""
        meta = None

        try:
            text, meta = await self._provider.complete(messages, self.model, **kwargs)
        except Exception as exc:
            status = "error"
            error_code = type(exc).__name__
            error_message = str(exc)
            raise
        finally:
            completed_at = datetime.now(timezone.utc)
            latency_ms = int((completed_at - started_at).total_seconds() * 1000)
            last_user = next(
                (m.content for m in reversed(messages) if m.role == "user"), ""
            )
            event = InferenceEvent(
                session_id=self.session_id,
                provider=self.provider,
                model=self.model,
                sdk_version=__version__,
                started_at=started_at,
                completed_at=completed_at,
                latency_ms=latency_ms,
                is_streaming=False,
                input_tokens=meta.input_tokens if meta else None,
                output_tokens=meta.output_tokens if meta else None,
                status=status,
                error_code=error_code,
                error_message=error_message,
                input_preview=truncate_preview(last_user),
                output_preview=truncate_preview(text),
                provider_request_id=meta.request_id if meta else None,
                client_metadata=self.metadata,
            )
            await self._emit(event)

        return text

    async def stream(
        self, messages: list[ChatMessage], **kwargs
    ) -> AsyncIterator[StreamChunk]:
        tracker = StreamingTracker()
        status: str = "success"
        error_code: str | None = None
        error_message: str | None = None
        meta = None

        try:
            async for chunk, chunk_meta in self._provider.stream(
                messages, self.model, **kwargs
            ):
                if self._cancelled:
                    status = "cancelled"
                    break

                if chunk.is_final:
                    meta = chunk_meta
                    break

                tracker.record_chunk(chunk.text)
                yield chunk

        except asyncio.CancelledError:
            status = "cancelled"
            raise
        except Exception as exc:
            status = "error"
            error_code = type(exc).__name__
            error_message = str(exc)
            raise
        finally:
            completed_at = datetime.now(timezone.utc)
            latency_ms = int(
                (completed_at - tracker.started_at).total_seconds() * 1000
            )
            last_user = next(
                (m.content for m in reversed(messages) if m.role == "user"), ""
            )
            event = InferenceEvent(
                session_id=self.session_id,
                provider=self.provider,
                model=self.model,
                sdk_version=__version__,
                started_at=tracker.started_at,
                completed_at=completed_at,
                latency_ms=latency_ms,
                time_to_first_token_ms=tracker.ttft_ms,
                is_streaming=True,
                stream_chunks=tracker.chunk_count,
                input_tokens=meta.input_tokens if meta else None,
                output_tokens=meta.output_tokens if meta else None,
                status=status,
                error_code=error_code,
                error_message=error_message,
                input_preview=truncate_preview(last_user),
                output_preview=truncate_preview(tracker.full_text),
                provider_request_id=meta.request_id if meta else None,
                client_metadata=self.metadata,
            )
            await self._emit(event)

    async def _emit(self, event: InferenceEvent) -> None:
        if not self.emit_logs or self.redis_client is None:
            return
        await emit_event(self.redis_client, self.stream_key, event)
