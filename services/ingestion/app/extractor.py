import uuid
from datetime import datetime, timezone

from llm_sdk.models import InferenceEvent

from .pii_client import PresidioClient


async def enrich(event: InferenceEvent, pii: PresidioClient) -> dict:
    """Redact PII on preview fields and return a dict ready for DB insert."""
    input_preview = await pii.redact(event.input_preview)
    output_preview = await pii.redact(event.output_preview)
    error_message = await pii.redact(event.error_message)

    completed_at = event.completed_at
    latency_ms = event.latency_ms
    if completed_at and event.started_at and latency_ms is None:
        # recompute if SDK didn't set it
        latency_ms = int((completed_at - event.started_at).total_seconds() * 1000)

    return {
        "id": str(uuid.uuid4()),
        "session_id": event.session_id or None,
        "provider": event.provider,
        "model": event.model,
        "provider_request_id": event.provider_request_id,
        "started_at": event.started_at,
        "completed_at": completed_at,
        "latency_ms": latency_ms,
        "time_to_first_token_ms": event.time_to_first_token_ms,
        "input_tokens": event.input_tokens,
        "output_tokens": event.output_tokens,
        "status": event.status,
        "error_code": event.error_code,
        "error_message": error_message,
        "input_preview": input_preview,
        "output_preview": output_preview,
        "is_streaming": event.is_streaming,
        "stream_chunks": event.stream_chunks,
        "sdk_version": event.sdk_version,
        "client_metadata": event.client_metadata or {},
    }
