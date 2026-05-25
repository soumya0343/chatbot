from __future__ import annotations

_PREVIEW_MAX_CHARS = 500


def truncate_preview(text: str | None, max_chars: int = _PREVIEW_MAX_CHARS) -> str | None:
    """Fast structural truncation — no semantic PII analysis (that happens in ingestion service)."""
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"
