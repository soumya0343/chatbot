from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..models.message import Message
from ..models.session import ChatSession
from ..schemas.session import (
    MessageResponse,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    SessionWithMessages,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    session = ChatSession(
        id=str(uuid.uuid4()),
        provider=body.provider,
        model=body.model,
        title=body.title,
        status="active",
        message_count=0,
        total_tokens=0,
        metadata_={},
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(ChatSession.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{session_id}", response_model=SessionWithMessages)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    msgs_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.sequence_num)
    )
    messages = msgs_result.scalars().all()

    return SessionWithMessages(
        id=session.id,
        title=session.title,
        provider=session.provider,
        model=session.model,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=session.message_count,
        total_tokens=session.total_tokens,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.sequence_num)
    )
    return result.scalars().all()


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.title is not None:
        session.title = body.title
    if body.status is not None:
        session.status = body.status
    session.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
