from __future__ import annotations

from types import SimpleNamespace

import pytest

from llm_sdk.models import ChatMessage
from llm_sdk.providers.sarvam import SARVAM_BASE_URL, SarvamProvider


def _chunk(content=None, usage=None, cid="req-1"):
    """Build a fake OpenAI-style streaming chunk."""
    choices = []
    if content is not None:
        choices = [SimpleNamespace(delta=SimpleNamespace(content=content))]
    return SimpleNamespace(id=cid, usage=usage, choices=choices)


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        async def gen():
            for c in self._chunks:
                yield c

        return gen()


class _FakeCompletions:
    def __init__(self, *, complete_response=None, stream_chunks=None):
        self._complete_response = complete_response
        self._stream_chunks = stream_chunks

    async def create(self, *, stream=False, **kwargs):
        if stream:
            return _FakeStream(self._stream_chunks)
        return self._complete_response


def _install_fake(provider, *, complete_response=None, stream_chunks=None):
    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=_FakeCompletions(
                complete_response=complete_response,
                stream_chunks=stream_chunks,
            )
        )
    )


def test_base_url_and_key_wiring():
    provider = SarvamProvider(api_key="test-key")
    assert str(provider._client.base_url).rstrip("/") == SARVAM_BASE_URL
    assert provider._client.api_key == "test-key"


@pytest.mark.asyncio
async def test_complete_returns_text_and_token_meta():
    provider = SarvamProvider(api_key="x")
    response = SimpleNamespace(
        id="req-42",
        choices=[SimpleNamespace(message=SimpleNamespace(content="hi there"))],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=3),
    )
    _install_fake(provider, complete_response=response)

    text, meta = await provider.complete([ChatMessage(role="user", content="hi")], "sarvam-m")

    assert text == "hi there"
    assert meta.request_id == "req-42"
    assert meta.input_tokens == 11
    assert meta.output_tokens == 3


@pytest.mark.asyncio
async def test_stream_yields_text_then_final_with_usage():
    provider = SarvamProvider(api_key="x")
    chunks = [
        _chunk(content="he"),
        _chunk(content="llo"),
        _chunk(usage=SimpleNamespace(prompt_tokens=5, completion_tokens=2)),
    ]
    _install_fake(provider, stream_chunks=chunks)

    out = [pair async for pair in provider.stream([ChatMessage(role="user", content="hi")], "sarvam-m")]

    texts = [c.text for c, _ in out if not c.is_final]
    finals = [(c, m) for c, m in out if c.is_final]
    assert texts == ["he", "llo"]
    assert len(finals) == 1
    _, meta = finals[0]
    assert meta.request_id == "req-1"
    assert meta.input_tokens == 5
    assert meta.output_tokens == 2


@pytest.mark.asyncio
async def test_stream_emits_sentinel_when_no_usage_chunk():
    """Sarvam may not honor include_usage; we still emit exactly one final sentinel."""
    provider = SarvamProvider(api_key="x")
    chunks = [_chunk(content="hi"), _chunk(content=" world")]
    _install_fake(provider, stream_chunks=chunks)

    out = [pair async for pair in provider.stream([ChatMessage(role="user", content="hi")], "sarvam-m")]

    finals = [(c, m) for c, m in out if c.is_final]
    assert len(finals) == 1
    _, meta = finals[0]
    assert meta.request_id == "req-1"
    assert meta.input_tokens is None
    assert meta.output_tokens is None
