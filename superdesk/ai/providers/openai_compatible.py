import asyncio
import time
from typing import Any

import aiohttp
from quart_babel import gettext

from ..config import config as ai_config
from ..errors import AIErrorKind, AIProviderError
from .base import AIProviderClient, CompletionRequest, CompletionResult


#: A connection that could not be opened within this many seconds failed instantly, a refused
#: connection or a failed DNS lookup, and is tried once more. A slower failure is not: it has used up
#: time the run does not have.
CONNECT_RETRY_WITHIN = 2.0

#: Seconds to wait before trying a refused connection again
CONNECT_RETRY_DELAY = 0.5


def _clock() -> float:
    return time.monotonic()


class OpenAICompatibleClient(AIProviderClient):
    """Client for any service exposing the OpenAI chat completions API.

    Covers OpenAI itself as well as OpenRouter, Azure style gateways and local runtimes, which all
    accept ``POST {base_url}/chat/completions`` and ``GET {base_url}/models``.
    """

    async def complete(self, request: CompletionRequest) -> CompletionResult:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "temperature": request.temperature,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = await self._request("POST", "chat/completions", payload)

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise AIProviderError(
                AIErrorKind.INVALID_RESPONSE,
                gettext("The AI provider response did not contain a completion"),
            )

        usage = data.get("usage")
        if not isinstance(usage, dict):
            usage = {}

        return CompletionResult(
            content=content or "",
            model=data.get("model") or request.model,
            # The OpenAI-compatible wire format spells the counts ``prompt_tokens`` and
            # ``completion_tokens``. ``CompletionResult`` carries the neutral names every provider
            # type maps onto, so the two spellings differ on purpose.
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw_usage=usage,
        )

    async def list_models(self) -> list[str]:
        data = await self._request("GET", "models")

        try:
            return [str(entry["id"]) for entry in data["data"]]
        except (KeyError, IndexError, TypeError):
            raise AIProviderError(
                AIErrorKind.INVALID_RESPONSE,
                gettext("The AI provider response did not contain a model list"),
            )

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        """Send one request, trying again once when the connection could not be opened at all

        Only a connection that was never opened is tried again: the request was not sent, so the
        provider cannot have started on it, or charged for it. Any later failure is not retried.
        """

        timeout = ai_config.request_timeout
        started = _clock()

        try:
            try:
                return await self._send(method, path, payload, timeout)
            except aiohttp.ClientConnectorError:
                elapsed = _clock() - started
                if elapsed > CONNECT_RETRY_WITHIN or timeout - elapsed - CONNECT_RETRY_DELAY <= 0:
                    raise

                await asyncio.sleep(CONNECT_RETRY_DELAY)

                # A busy server can wake up well after the delay, so the time left is read again
                time_left = timeout - (_clock() - started)
                # aiohttp reads a total of zero or less as no timeout at all
                if time_left <= 0:
                    raise

                return await self._send(method, path, payload, time_left)
        except asyncio.TimeoutError:
            raise AIProviderError(
                AIErrorKind.TIMEOUT,
                gettext("The AI provider did not answer within {seconds} seconds").format(seconds=timeout),
            )
        except aiohttp.ClientError:
            raise AIProviderError(AIErrorKind.UPSTREAM, gettext("The AI provider could not be reached"))

    async def _send(self, method: str, path: str, payload: dict[str, Any] | None, timeout: float) -> Any:
        url = f"{self.base_url}/{path}"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                json=payload,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status >= 400:
                    raise self._error_for_status(response.status)

                try:
                    return await response.json(content_type=None)
                except ValueError:
                    raise AIProviderError(
                        AIErrorKind.INVALID_RESPONSE,
                        gettext("The AI provider answered with a body that is not JSON"),
                    )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        extra_headers = self.config.get("headers")
        if isinstance(extra_headers, dict):
            headers.update({str(name): str(value) for name, value in extra_headers.items()})

        return headers

    def _error_for_status(self, status: int) -> AIProviderError:
        if status in (401, 403):
            kind = AIErrorKind.AUTH
            message = gettext("The AI provider rejected the credentials (HTTP {status})")
        elif status == 429:
            kind = AIErrorKind.RATE_LIMIT
            message = gettext("The AI provider rate limit was reached (HTTP {status})")
        elif status >= 500:
            kind = AIErrorKind.UPSTREAM
            message = gettext("The AI provider failed to handle the request (HTTP {status})")
        else:
            kind = AIErrorKind.UPSTREAM
            message = gettext("The AI provider rejected the request (HTTP {status})")

        return AIProviderError(kind, message.format(status=status), status)
