"""Thin async client for 9router — an OpenAI-compatible LLM proxy.

Not Gemini (see Decisions/2026-09-15 - LLM provider adalah 9router, bukan
Gemini, in the vault) — this deliberately talks OpenAI chat-completions shape
over plain httpx (already a dependency), so no new SDK was needed.

Single-shot, constrained-JSON calls only — no streaming, no tool-calling.
Transient failures (timeouts, connection errors, 5xx) get a small manual
retry with backoff (no new dependency, e.g. `tenacity` — plain `asyncio.sleep`
is enough for this call volume); 4xx responses are not retried since retrying
a bad request/auth failure can't succeed.
"""
import asyncio
import json

import httpx

_MAX_ATTEMPTS = 3
_BASE_BACKOFF_SECONDS = 0.5


class LLMResponseError(Exception):
    """Raised when 9router returns an HTTP error, a non-JSON body, or JSON
    that doesn't parse as an object. Callers (Evaluator/Diagnostician) decide
    what to do next — this class only reports that the contract was broken."""


class LLMClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # One shared connection pool for the lifetime of this client, instead
        # of a fresh TCP+TLS handshake per call — call aclose() when done
        # (app shutdown, or end of a one-off script like eval/run_eval.py).
        self._client = httpx.AsyncClient(timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def complete_json(self, model: str, system_prompt: str, user_prompt: str) -> dict:
        """POST {base_url}/chat/completions with response_format=json_object,
        return the parsed JSON body of choices[0].message.content.

        response_format only guarantees the reply IS JSON, not its shape —
        callers must still validate the keys/values they expect.
        """
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"

        response: httpx.Response | None = None
        for attempt in range(_MAX_ATTEMPTS):
            is_last_attempt = attempt == _MAX_ATTEMPTS - 1
            try:
                response = await self._client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or is_last_attempt:
                    raise LLMResponseError(f"9router request failed: {exc}") from exc
            except httpx.HTTPError as exc:
                if is_last_attempt:
                    raise LLMResponseError(f"9router request failed: {exc}") from exc
            await asyncio.sleep(_BASE_BACKOFF_SECONDS * (2**attempt))

        assert response is not None  # loop always raises or breaks with a response
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMResponseError(f"9router response was not the expected JSON shape: {exc}") from exc

        if not isinstance(parsed, dict):
            raise LLMResponseError(f"9router JSON content was not an object: {parsed!r}")

        return parsed
