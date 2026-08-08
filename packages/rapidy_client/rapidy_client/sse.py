from __future__ import annotations

import asyncio
import codecs
import json
import logging
import random
import sys
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator
from dataclasses import dataclass, field
from types import ModuleType
from typing import TYPE_CHECKING, Any, Generic, Literal, TypeVar, cast

from pydantic import TypeAdapter, ValidationError

from rapidy_client._models import QueryValue, Timeout
from rapidy_client.config import BackoffConfig
from rapidy_client.errors import (
    ClientClosedError,
    DecodeError,
    HttpClientError,
    MessageValidationError,
    StatusError,
    TransportError,
)

if TYPE_CHECKING:
    from pydantic import BaseModel

    from rapidy_client._client import HttpClient
    from rapidy_client._models import Response

TModel = TypeVar("TModel", bound="BaseModel")
TEvent = TypeVar("TEvent")

__all__ = ["SSEConnect", "SSEReconnect", "SSEStream", "ServerSentEvent"]

_LOGGER = logging.getLogger("rapidy_client.sse")
_RNG = random.Random()


@dataclass(slots=True)
class ServerSentEvent:
    id: str | None = None
    event: str | None = None
    data: str = ""
    retry: int | None = None

    def json(self) -> Any:
        try:
            return json.loads(self.data)
        except json.JSONDecodeError as exc:
            raise DecodeError("SSE event data is not valid JSON") from exc

    def as_model(self, model: type[TModel]) -> TModel:
        try:
            return model.model_validate_json(self.data)
        except ValidationError as exc:
            raise MessageValidationError(
                f"SSE event data is invalid for {model.__name__}"
            ) from exc


@dataclass(slots=True, kw_only=True)
class SSEReconnect:
    backoff: BackoffConfig = field(
        default_factory=lambda: BackoffConfig(base=1.0, cap=60.0)
    )
    max_attempts: int | None = None
    honor_retry_field: bool = True

    def __post_init__(self) -> None:
        if self.max_attempts is not None and self.max_attempts <= 0:
            raise ValueError("max_attempts must be greater than zero or None")


# Adapted from httpx-sse's MIT-licensed decoder by Florimond Manca.
# The upstream license is retained in docs/vendor/httpx-sse-LICENSE.
class SSEDecoder:
    """Incremental WHATWG event-stream decoder."""

    def __init__(self) -> None:
        self._event: str | None = None
        self._data: list[str] = []
        self._last_event_id: str | None = None
        self._retry: int | None = None

    def decode(self, line: str) -> ServerSentEvent | None:
        if not line:
            if not self._data and self._event is None and self._retry is None:
                return None
            event = ServerSentEvent(
                id=self._last_event_id,
                event=self._event,
                data="\n".join(self._data),
                retry=self._retry,
            )
            self._event = None
            self._data = []
            self._retry = None
            return event
        if line.startswith(":"):
            return None

        name, separator, value = line.partition(":")
        if not separator:
            value = ""
        elif value.startswith(" "):
            value = value[1:]
        if name == "event":
            self._event = value
        elif name == "data":
            self._data.append(value)
        elif name == "id" and "\x00" not in value:
            self._last_event_id = value
        elif name == "retry" and value.isdigit():
            self._retry = int(value)
        return None

    async def iter_bytes(
        self,
        chunks: AsyncIterable[bytes],
    ) -> AsyncIterator[ServerSentEvent]:
        async for line in _aiter_sse_lines(chunks):
            event = self.decode(line)
            if event is not None:
                yield event


async def _aiter_sse_lines(chunks: AsyncIterable[bytes]) -> AsyncIterator[str]:
    decoder = codecs.getincrementaldecoder("utf-8")()
    buffer = ""
    at_start = True

    async def decoded() -> AsyncIterator[str]:
        nonlocal at_start, buffer
        async for chunk in chunks:
            try:
                text = decoder.decode(chunk)
            except UnicodeDecodeError as exc:
                raise DecodeError("SSE stream is not valid UTF-8") from exc
            if text and at_start:
                text = text.removeprefix("\ufeff")
                at_start = False
            buffer += text
            while True:
                cr = buffer.find("\r")
                lf = buffer.find("\n")
                positions = tuple(index for index in (cr, lf) if index >= 0)
                if not positions:
                    break
                index = min(positions)
                if buffer[index] == "\r" and index + 1 == len(buffer):
                    break
                consume = 2 if buffer[index : index + 2] == "\r\n" else 1
                line = buffer[:index]
                buffer = buffer[index + consume :]
                yield line

    async for line in decoded():
        yield line
    try:
        tail = decoder.decode(b"", final=True)
    except UnicodeDecodeError as exc:
        raise DecodeError("SSE stream ended in invalid UTF-8") from exc
    if tail and at_start:
        tail = tail.removeprefix("\ufeff")
    buffer += tail
    if buffer.endswith("\r"):
        yield buffer[:-1]
    elif buffer:
        yield buffer


def _sse_backoff(
    reconnect: SSEReconnect,
    exponent: int,
    retry_ms: int | None,
) -> float:
    base = reconnect.backoff.base
    if reconnect.honor_retry_field and retry_ms is not None:
        base = retry_ms / 1000.0
    ceiling: float = min(
        float(reconnect.backoff.cap),
        float(base) * (2**exponent),
    )
    if reconnect.backoff.jitter == "full":
        return _RNG.uniform(0.0, ceiling)
    return ceiling


class SSEConnect(Generic[TEvent]):
    """A lazy SSE stream with Last-Event-ID aware reconnects."""

    def __init__(
        self,
        client: HttpClient,
        path: str,
        *,
        last_event_id: str | None = None,
        reconnect: SSEReconnect | None = None,
        headers: dict[str, str] | None = None,
        _adapter: TypeAdapter[Any] | None = None,
        _on_invalid: Literal["raise", "skip"] = "raise",
        _path_params: dict[str, object] | None = None,
        _query: dict[str, QueryValue] | None = None,
    ) -> None:
        if _on_invalid not in {"raise", "skip"}:
            raise ValueError("on_invalid must be 'raise' or 'skip'")
        self._client = client
        self._path = path
        self._last_event_id = last_event_id
        self._reconnect = reconnect or SSEReconnect()
        self._headers = dict(headers or {})
        self._adapter = _adapter
        self._on_invalid = _on_invalid
        self._path_params = _path_params
        self._query = _query
        self._response: Response | None = None
        self._events_iter: AsyncGenerator[TEvent, None] | None = None
        self._next_task: asyncio.Future[TEvent] | None = None
        self._entered = False
        self._closed = False

    @property
    def last_event_id(self) -> str | None:
        return self._last_event_id

    async def __aenter__(self) -> AsyncIterator[TEvent]:
        if self._entered:
            raise RuntimeError("SSE context manager cannot be entered twice")
        if self._client._closing:
            raise ClientClosedError("HttpClient is closed")
        self._entered = True
        self._client._bind_loop()
        self._client._infinite.add(self)
        self._events_iter = self._events()
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        del exc_type, exc, tb
        await self.aclose()

    def __aiter__(self) -> SSEConnect[TEvent]:
        return self

    async def __anext__(self) -> TEvent:
        if self._closed:
            raise StopAsyncIteration
        if self._events_iter is None:
            raise RuntimeError("SSEConnect must be entered before iteration")
        if self._next_task is not None:
            raise RuntimeError("SSEConnect already has an active consumer")
        task: asyncio.Future[TEvent] = asyncio.ensure_future(anext(self._events_iter))
        self._next_task = task
        try:
            return await task
        except asyncio.CancelledError:
            if self._closed:
                raise ClientClosedError(
                    "HttpClient closed while SSE receive was in flight"
                ) from None
            raise
        finally:
            self._next_task = None

    def _convert(self, event: ServerSentEvent) -> TEvent | None:
        if self._adapter is None:
            return cast("TEvent", event)
        try:
            return cast("TEvent", self._adapter.validate_json(event.data))
        except ValidationError as exc:
            if self._on_invalid == "raise":
                raise MessageValidationError(
                    "invalid typed SSE event",
                    upstream=self._client._name,
                    endpoint=self._path,
                ) from exc
            _LOGGER.debug("skipping invalid SSE event: %s", exc)
            return None

    async def _events(self) -> AsyncGenerator[TEvent, None]:
        reconnect = self._reconnect
        attempt = 0
        retry_ms: int | None = None
        while not self._closed and not self._client._closing:
            headers = {"Accept": "text/event-stream", **self._headers}
            if self._last_event_id is not None:
                headers["Last-Event-ID"] = self._last_event_id
            configured = self._client._config.timeout
            timeout = Timeout(
                total=None,
                connect=configured.connect,
                read=120.0,
                write=configured.write,
                pool=configured.pool,
            )
            request = self._client._build_request(
                "GET",
                self._path,
                path_params=self._path_params,
                query=self._query,
                headers=headers,
                timeout=timeout,
                stream=True,
            )
            try:
                self._response = await self._client._entry(request)
                if self._response.status != 200:
                    raise StatusError(
                        f"SSE connection returned status {self._response.status}",
                        status=self._response.status,
                        response=self._response,
                        upstream=request.extensions.upstream,
                        endpoint=request.extensions.endpoint,
                        request_id=request.extensions.request_id,
                    )
                attempt = 0
                decoder = SSEDecoder()
                async for event in decoder.iter_bytes(self._response.aiter_bytes()):
                    if self._closed or self._client._closing:
                        return
                    if event.id is not None:
                        self._last_event_id = event.id
                    if event.retry is not None:
                        retry_ms = event.retry
                    converted = self._convert(event)
                    if converted is not None:
                        yield converted
            except ClientClosedError:
                return
            except HttpClientError as exc:
                if not isinstance(exc, TransportError):
                    raise
            finally:
                response = self._response
                self._response = None
                if response is not None:
                    await response.aclose()

            if self._closed or self._client._closing:
                return
            attempt += 1
            if reconnect.max_attempts is not None and attempt >= reconnect.max_attempts:
                return
            await self._client._clock.sleep(
                _sse_backoff(reconnect, attempt - 1, retry_ms)
            )

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._client._infinite.discard(self)
        task = self._next_task
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        response = self._response
        if response is not None:
            await response.aclose()
        iterator = self._events_iter
        if iterator is not None and task is None:
            await iterator.aclose()


class SSEStream(Generic[TEvent]):
    """Typed declarative SSE stream with an observable resume checkpoint."""

    def __init__(self, connection: SSEConnect[TEvent]) -> None:
        self._connection = connection
        self._iterator: AsyncIterator[TEvent] | None = None

    @property
    def last_event_id(self) -> str | None:
        return self._connection.last_event_id

    async def __aenter__(self) -> SSEStream[TEvent]:
        self._iterator = await self._connection.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        await self._connection.__aexit__(exc_type, exc, tb)

    def __aiter__(self) -> SSEStream[TEvent]:
        return self

    async def __anext__(self) -> TEvent:
        if self._iterator is None:
            raise RuntimeError("SSEStream must be entered before iteration")
        return await anext(self._iterator)


class _CallableSSEModule(ModuleType):
    """Keep ``from rapidy_client import sse`` callable after submodule loading."""

    def __call__(
        self,
        path: str,
        *,
        reconnect: SSEReconnect | None = None,
        on_invalid: Literal["raise", "skip"] = "raise",
        last_event_id: str | None = None,
    ) -> Any:
        from rapidy_client._typed import sse

        return sse(
            path,
            reconnect=reconnect,
            on_invalid=on_invalid,
            last_event_id=last_event_id,
        )


sys.modules[__name__].__class__ = _CallableSSEModule
