"""Tests for LLMClient — retry/backoff and response parsing.

Uses httpx.MockTransport (part of httpx itself, no new dependency) instead of
a live 9router endpoint, so these stay in the "no live network in automated
tests" pattern used by the rest of the suite.
"""
import httpx
import pytest

from app.core.llm_client import LLMClient, LLMResponseError


def _client_with_handler(handler) -> LLMClient:
    client = LLMClient(base_url="http://fake-9router/v1", api_key="test-key")
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0)
    return client


async def _no_sleep(_seconds):
    return None


@pytest.mark.asyncio
async def test_complete_json_success_on_first_try():
    def handler(_request):
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": true}'}}]})

    client = _client_with_handler(handler)
    result = await client.complete_json("model", "sys", "user")
    assert result == {"ok": True}
    await client.aclose()


@pytest.mark.asyncio
async def test_complete_json_retries_on_5xx_then_succeeds(monkeypatch):
    monkeypatch.setattr("app.core.llm_client.asyncio.sleep", _no_sleep)
    calls = {"n": 0}

    def handler(_request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"ok": true}'}}]})

    client = _client_with_handler(handler)
    result = await client.complete_json("model", "sys", "user")
    assert calls["n"] == 3
    assert result == {"ok": True}
    await client.aclose()


@pytest.mark.asyncio
async def test_complete_json_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("app.core.llm_client.asyncio.sleep", _no_sleep)
    calls = {"n": 0}

    def handler(_request):
        calls["n"] += 1
        return httpx.Response(503)

    client = _client_with_handler(handler)
    with pytest.raises(LLMResponseError):
        await client.complete_json("model", "sys", "user")
    assert calls["n"] == 3  # _MAX_ATTEMPTS, no more
    await client.aclose()


@pytest.mark.asyncio
async def test_complete_json_does_not_retry_on_4xx(monkeypatch):
    monkeypatch.setattr("app.core.llm_client.asyncio.sleep", _no_sleep)
    calls = {"n": 0}

    def handler(_request):
        calls["n"] += 1
        return httpx.Response(401)

    client = _client_with_handler(handler)
    with pytest.raises(LLMResponseError):
        await client.complete_json("model", "sys", "user")
    assert calls["n"] == 1  # never retried
    await client.aclose()


@pytest.mark.asyncio
async def test_complete_json_rejects_non_json_content():
    def handler(_request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]})

    client = _client_with_handler(handler)
    with pytest.raises(LLMResponseError):
        await client.complete_json("model", "sys", "user")
    await client.aclose()


@pytest.mark.asyncio
async def test_complete_json_reuses_the_same_underlying_client():
    def handler(_request):
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = _client_with_handler(handler)
    underlying = client._client
    await client.complete_json("model", "sys", "user")
    await client.complete_json("model", "sys", "user")
    assert client._client is underlying  # not recreated per call
    await client.aclose()
