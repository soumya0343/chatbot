from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from llm_sdk import ChatMessage, TrackedClient

from ..database import AsyncSessionLocal
from ..dependencies import get_presidio_client, get_redis
from ..models.message import Message
from ..models.session import ChatSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

CONTEXT_WINDOW = 20  # max messages sent as history to LLM


async def _redact(presidio_client, text: str) -> str:
    """Call Presidio sidecar. Falls back to original text on any error."""
    try:
        response = await presidio_client.post(
            "/analyze_and_anonymize",
            json={"text": text, "language": "en"},
            timeout=5.0,
        )
        return response.json()["anonymized_text"]
    except Exception as e:
        logger.warning(f"Presidio redaction failed, using original text: {e}")
        return text


async def _get_session_or_404(db: AsyncSession, session_id: str) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _next_sequence(db: AsyncSession, session_id: str) -> int:
    result = await db.execute(
        select(func.coalesce(func.max(Message.sequence_num), 0)).where(
            Message.session_id == session_id
        )
    )
    return (result.scalar() or 0) + 1


async def _load_history(db: AsyncSession, session_id: str) -> list[ChatMessage]:
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.sequence_num.desc())
        .limit(CONTEXT_WINDOW)
    )
    rows = result.scalars().all()
    # reverse so oldest-first for LLM context
    return [ChatMessage(role=m.role, content=m.content) for m in reversed(rows)]


@router.get("/sessions/{session_id}/stream")
async def stream_chat(
    session_id: str,
    request: Request,
    user_message: str = Query(..., min_length=1),
    provider: Literal["anthropic", "openai", "gemini"] = Query(...),
    model: str = Query(...),
    redis=Depends(get_redis),
    presidio_client=Depends(get_presidio_client),
):
    async def event_generator():
        async with AsyncSessionLocal() as db:
            try:
                # 1. Verify session
                session = await db.get(ChatSession, session_id)
                if not session:
                    yield _sse({"type": "error", "error": "Session not found"})
                    return

                # 2. PII-redact user message before storing
                clean_user_msg = await _redact(presidio_client, user_message)

                # 3. Store user message
                seq = await _next_sequence(db, session_id)
                user_msg_row = Message(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    role="user",
                    content=clean_user_msg,
                    content_preview=clean_user_msg[:200],
                    sequence_num=seq,
                    metadata_={},
                )
                db.add(user_msg_row)
                await db.commit()
                await db.refresh(user_msg_row)

                # 4. Auto-title on first message
                if session.message_count == 0 and not session.title:
                    session.title = clean_user_msg[:60]

                # 5. Load conversation history (includes the message we just stored)
                history = await _load_history(db, session_id)

                # 6. Stream from LLM
                client = TrackedClient(
                    provider=provider,
                    model=model,
                    session_id=session_id,
                    redis_client=redis,
                    emit_logs=True,
                )

                response_parts: list[str] = []

                async for chunk in client.stream(history):
                    if await request.is_disconnected():
                        await client.cancel()
                        break
                    response_parts.append(chunk.text)
                    yield _sse({"type": "chunk", "text": chunk.text})

                # 7. Store assistant response
                full_response = "".join(response_parts)
                if full_response:
                    seq = await _next_sequence(db, session_id)
                    assistant_msg_row = Message(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        role="assistant",
                        content=full_response,
                        content_preview=full_response[:200],
                        sequence_num=seq,
                        metadata_={},
                    )
                    db.add(assistant_msg_row)

                # 8. Update session aggregates
                session.message_count = session.message_count + (2 if full_response else 1)
                session.updated_at = datetime.now(timezone.utc)
                await db.commit()

                yield _sse({"type": "done"})
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.exception(f"Stream error for session {session_id}")
                yield _sse({"type": "error", "error": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"
