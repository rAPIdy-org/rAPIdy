from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, cast, runtime_checkable

from rapidy_client._models import URL, Response
from rapidy_client._redaction import CROP_SUFFIX, DEFAULT_REDACTOR, Redactor
from rapidy_client.config import LogConfig

_HOOK_LOGGER = logging.getLogger("rapidy_client.observability")
_HTTP_LOGGER = logging.getLogger("rapidy_client.http")

RETRY_REASON_AUTH_401 = "auth_401"
RETRY_REASON_BUDGET_EXHAUSTED = "budget_exhausted"


def retry_reason_status(status: int) -> str:
    return f"status_{status}"


def retry_reason_network(exc: BaseException) -> str:
    return f"network_{type(exc).__name__}"


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestContext:
    upstream: str
    method: str
    endpoint: str | None
    url: URL
    attempt: int
    request_id: str | None
    started_at: float
    elapsed: float | None = None


@runtime_checkable
class Observer(Protocol):
    async def on_request_start(self, ctx: RequestContext) -> None: ...

    async def on_request_end(
        self,
        ctx: RequestContext,
        response: Response,
    ) -> None: ...

    async def on_request_error(
        self,
        ctx: RequestContext,
        exc: Exception,
    ) -> None: ...

    async def on_attempt_start(self, ctx: RequestContext) -> None: ...

    async def on_attempt_end(
        self,
        ctx: RequestContext,
        response: Response | None,
        exc: Exception | None,
    ) -> None: ...

    async def on_retry(
        self,
        ctx: RequestContext,
        attempt: int,
        reason: str,
        delay: float,
    ) -> None: ...

    async def on_breaker_transition(
        self,
        upstream: str,
        old: str,
        new: str,
    ) -> None: ...

    async def on_pool_wait(self, upstream: str, waited: float) -> None: ...

    async def on_connection_open(
        self,
        upstream: str,
        reused: bool,
        dns: float,
        connect: float,
    ) -> None: ...


class BaseObserver:
    async def on_request_start(self, ctx: RequestContext) -> None:
        del ctx

    async def on_request_end(
        self,
        ctx: RequestContext,
        response: Response,
    ) -> None:
        del ctx, response

    async def on_request_error(
        self,
        ctx: RequestContext,
        exc: Exception,
    ) -> None:
        del ctx, exc

    async def on_attempt_start(self, ctx: RequestContext) -> None:
        del ctx

    async def on_attempt_end(
        self,
        ctx: RequestContext,
        response: Response | None,
        exc: Exception | None,
    ) -> None:
        del ctx, response, exc

    async def on_retry(
        self,
        ctx: RequestContext,
        attempt: int,
        reason: str,
        delay: float,
    ) -> None:
        del ctx, attempt, reason, delay

    async def on_breaker_transition(
        self,
        upstream: str,
        old: str,
        new: str,
    ) -> None:
        del upstream, old, new

    async def on_pool_wait(self, upstream: str, waited: float) -> None:
        del upstream, waited

    async def on_connection_open(
        self,
        upstream: str,
        reused: bool,
        dns: float,
        connect: float,
    ) -> None:
        del upstream, reused, dns, connect


async def notify_observers(
    observers: Sequence[Observer],
    hook: str,
    *args: object,
    logger: logging.Logger = _HOOK_LOGGER,
) -> None:
    for observer in observers:
        method = cast(
            "Callable[..., Awaitable[None]] | None",
            getattr(observer, hook, None),
        )
        if method is None:
            continue
        try:
            await method(*args)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "observer %r hook %s raised; request continues",
                type(observer).__name__,
                hook,
            )


def _request_body(response: Response | None) -> bytes | None:
    if response is None:
        return None
    content = response.request.content
    return content if isinstance(content, bytes) else None


def _response_body(response: Response | None) -> bytes | None:
    if response is None:
        return None
    return response._buffered


class LoggingObserver(BaseObserver):
    def __init__(
        self,
        config: LogConfig,
        *,
        logger: logging.Logger | None = None,
        redactor: Redactor | None = None,
    ) -> None:
        self._level = config.level
        self._max_body_len = config.max_body_len
        self._logger = logger if logger is not None else _HTTP_LOGGER
        base = redactor if redactor is not None else DEFAULT_REDACTOR
        self._redactor = base.extend(
            headers=config.redact_headers_extra,
            query=config.redact_query_extra,
        )

    async def on_request_end(
        self,
        ctx: RequestContext,
        response: Response,
    ) -> None:
        if self._level != "off":
            self._emit(ctx, response=response, exc=None)

    async def on_request_error(
        self,
        ctx: RequestContext,
        exc: Exception,
    ) -> None:
        if self._level != "off":
            self._emit(ctx, response=None, exc=exc)

    def _body_preview(self, raw: bytes | None) -> str | None:
        if raw is None:
            return None
        cropped = len(raw) > self._max_body_len
        selected = raw[: self._max_body_len] if cropped else raw
        text = selected.decode("utf-8", errors="replace")
        if cropped:
            text += CROP_SUFFIX
        return self._redactor.redact_text(text)

    def _emit(
        self,
        ctx: RequestContext,
        *,
        response: Response | None,
        exc: Exception | None,
    ) -> None:
        payload: dict[str, object] = {
            "event": "http_request",
            "upstream": ctx.upstream,
            "method": ctx.method,
            "endpoint": ctx.endpoint,
            "url": self._redactor.redact_url_str(ctx.url._raw_str()),
            "status": response.status if response is not None else None,
            "duration_ms": (
                round(ctx.elapsed * 1000, 3) if ctx.elapsed is not None else None
            ),
            "attempt": ctx.attempt,
            "request_id": ctx.request_id,
            "error": type(exc).__name__ if exc is not None else None,
        }
        if self._level in {"headers", "body"}:
            payload["request_headers"] = (
                self._redactor.redact_headers(response.request.headers.multi_items())
                if response is not None
                else None
            )
            payload["response_headers"] = (
                self._redactor.redact_headers(response.headers.multi_items())
                if response is not None
                else None
            )
        if self._level == "body":
            payload["request_body"] = self._body_preview(_request_body(response))
            payload["response_body"] = self._body_preview(_response_body(response))
        self._logger.info(json.dumps(payload, ensure_ascii=False, default=str))


__all__ = (
    "RETRY_REASON_AUTH_401",
    "RETRY_REASON_BUDGET_EXHAUSTED",
    "BaseObserver",
    "LoggingObserver",
    "Observer",
    "RequestContext",
    "notify_observers",
    "retry_reason_network",
    "retry_reason_status",
)
