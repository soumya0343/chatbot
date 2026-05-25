from __future__ import annotations

from datetime import datetime, timezone


class StreamingTracker:
    """Tracks timing and content for a single streaming LLM call."""

    def __init__(self) -> None:
        self.started_at: datetime = datetime.now(timezone.utc)
        self._first_token_at: datetime | None = None
        self.chunk_count: int = 0
        self._parts: list[str] = []

    def record_chunk(self, text: str) -> None:
        if text and self._first_token_at is None:
            self._first_token_at = datetime.now(timezone.utc)
        self.chunk_count += 1
        self._parts.append(text)

    @property
    def ttft_ms(self) -> int | None:
        if self._first_token_at is None:
            return None
        delta = self._first_token_at - self.started_at
        return max(0, int(delta.total_seconds() * 1000))

    @property
    def full_text(self) -> str:
        return "".join(self._parts)
