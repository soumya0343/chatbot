from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderMeta(BaseModel):
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class StreamChunk(BaseModel):
    text: str
    is_final: bool = False


class InferenceEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_version: str = "1.0"

    session_id: str
    provider: str
    model: str
    sdk_version: str

    started_at: datetime
    completed_at: datetime | None = None
    latency_ms: int | None = None
    time_to_first_token_ms: int | None = None

    is_streaming: bool = False
    stream_chunks: int | None = None

    input_tokens: int | None = None
    output_tokens: int | None = None

    status: Literal["success", "error", "cancelled", "timeout"] = "success"
    error_code: str | None = None
    error_message: str | None = None

    input_preview: str | None = None   # last user message, truncated to 500 chars
    output_preview: str | None = None  # assistant response, truncated to 500 chars

    provider_request_id: str | None = None
    client_metadata: dict = Field(default_factory=dict)
