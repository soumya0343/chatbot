from __future__ import annotations

import logging

from .models import InferenceEvent

logger = logging.getLogger(__name__)


async def emit_event(redis_client, stream_key: str, event: InferenceEvent) -> None:
    """Publish InferenceEvent to Redis Streams. Never raises — logging must not crash the app."""
    try:
        payload = event.model_dump_json()
        await redis_client.xadd(stream_key, {"data": payload})
    except Exception as e:
        logger.error(f"Failed to emit inference event {event.event_id}: {e}")
