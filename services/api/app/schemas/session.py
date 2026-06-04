from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    provider: Literal["anthropic", "openai", "gemini", "sarvam", "groq"]
    model: str
    title: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    status: Literal["active", "cancelled", "archived"] | None = None


class SessionResponse(BaseModel):
    id: str
    title: str | None
    provider: str
    model: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    total_tokens: int

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    sequence_num: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionWithMessages(SessionResponse):
    messages: list[MessageResponse] = Field(default_factory=list)
