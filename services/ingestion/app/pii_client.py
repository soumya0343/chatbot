import logging

import httpx

logger = logging.getLogger(__name__)


class PresidioClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=5.0)

    async def redact(self, text: str | None) -> str | None:
        """Redact PII from text. Fails open — returns original on any error."""
        if not text or not text.strip():
            return text
        try:
            r = await self._client.post(
                "/analyze_and_anonymize",
                json={"text": text, "language": "en"},
            )
            r.raise_for_status()
            return r.json()["anonymized_text"]
        except Exception as e:
            logger.warning(f"Presidio redaction failed (fail-open): {e}")
            return text

    async def aclose(self) -> None:
        await self._client.aclose()
