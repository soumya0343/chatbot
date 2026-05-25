import logging

from llm_sdk.models import InferenceEvent

logger = logging.getLogger(__name__)


def parse_event(msg_id: str, fields: dict) -> InferenceEvent | None:
    """Parse raw Redis Streams fields into InferenceEvent. Returns None on bad payload."""
    raw = fields.get("data")
    if not raw:
        logger.warning(f"Message {msg_id} has no 'data' field — skipping")
        return None
    try:
        return InferenceEvent.model_validate_json(raw)
    except Exception as e:
        logger.error(f"Failed to parse InferenceEvent from message {msg_id}: {e}")
        return None
