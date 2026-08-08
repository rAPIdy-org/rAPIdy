from __future__ import annotations

import codecs
import inspect
import json as _json
from collections.abc import (
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    TypedDict,
    TypeVar,
    runtime_checkable,
)
from uuid import UUID

import yarl

from rapidy_client._redaction import DEFAULT_REDACTOR
from rapidy_client.errors import BodyTooLargeError, DecodeError

if TYPE_CHECKING:
    from rapidy_core import Unset

    from rapidy_client._content import ContentFactory
    from rapidy_client.config import RedirectConfig, RetryConfig


class URL:
    __slots__ = ("_url",)

    def __init__(self, url: str | yarl.URL) -> None:
        self._url = url if isinstance(url, yarl.URL) else yarl.URL(url)

    @property
    def scheme(self) -> str:
        return self._url.scheme

    @property
    def host(self) -> str | None:
        return self._url.host

    @property
    def port(self) -> int | None:
        return self._url.port

    @property
    def path(self) -> str:
        return self._url.path

    @property
    def query_string(self) -> str:
        return self._url.query_string

    def origin(self) -> str:
        return str(self._url.origin())

    def join(self, path: str) -> URL:
        return URL(self._url.join(yarl.URL(path)))

    def with_query(self, query: Mapping[str, str]) -> URL:
        return URL(self._url.with_query(query))

    def _raw_str(self) -> str:
        return str(self._url)

    def __str__(self) -> str:
        return DEFAULT_REDACTOR.redact_url_str(str(self._url))

    def __repr__(self) -> str:
        value = DEFAULT_REDACTOR.redact_url_str(str(self._url))
        return f"URL({value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, URL):
            return NotImplemented
        return self._url == other._url

    def __hash__(self) -> int:
        return hash(self._url)


class Headers:
    __slots__ = ("_items",)

    def __init__(
        self,
        items: Mapping[str, str] | Iterable[tuple[str, str]] | None = None,
    ) -> None:
        if items is None:
            self._items: list[tuple[str, str]] = []
        elif isinstance(items, Mapping):
            self._items = list(items.items())
        else:
            self._items = list(items)

    def get(self, key: str, default: str | None = None) -> str | None:
        folded = key.casefold()
        for name, value in self._items:
            if name.casefold() == folded:
                return value
        return default

    def get_all(self, key: str) -> list[str]:
        folded = key.casefold()
        return [value for name, value in self._items if name.casefold() == folded]

    def multi_items(self) -> list[tuple[str, str]]:
        return self._items.copy()

    def __getitem__(self, key: str) -> str:
        folded = key.casefold()
        for name, value in self._items:
            if name.casefold() == folded:
                return value
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        folded = key.casefold()
        return any(name.casefold() == folded for name, _ in self._items)

    def __iter__(self) -> Iterator[str]:
        seen: set[str] = set()
        for name, _ in self._items:
            folded = name.casefold()
            if folded not in seen:
                seen.add(folded)
                yield name

    def __len__(self) -> int:
        return len({name.casefold() for name, _ in self._items})

    def __repr__(self) -> str:
        return f"Headers({DEFAULT_REDACTOR.redact_headers(self._items)!r})"


@dataclass(slots=True, kw_only=True)
class Timeout:
    total: float | None = 10.0
    connect: float = 3.0
    read: float = 10.0
    write: float = 30.0
    pool: float = 5.0


type QueryValue = (
    str
    | int
    | float
    | bool
    | UUID
    | datetime
    | date
    | Enum
    | None
    | Sequence[QueryValue]
)


@dataclass(slots=True, kw_only=True)
class RequestExtensions:
    upstream: str
    endpoint: str | None
    request_id: str | None
    timeout: Timeout
    retry: RetryConfig | None
    idempotent: bool
    auth_override: AuthPolicy | None | Unset
    deadline: float | None
    redirects: RedirectConfig
    declared_middlewares: tuple[Middleware, ...] = ()
    attempt: int = 0
    attempt_listeners: list[AttemptListener] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, kw_only=True)
class ResponseExtensions:
    elapsed: float
    attempt: int
    connection_reused: bool | None = None
    pool_wait: float | None = None


T = TypeVar("T")


@dataclass(slots=True, kw_only=True, frozen=True)
class Result(Generic[T]):
    value: T
    status: int
    headers: Headers


class Request:
    __slots__ = ("content", "extensions", "headers", "method", "url")

    def __init__(
        self,
        *,
        method: str,
        url: URL,
        headers: Headers,
        content: bytes | AsyncIterable[bytes] | ContentFactory | None,
        extensions: RequestExtensions,
    ) -> None:
        self.method = method
        self.url = url
        self.headers = headers
        self.content = content
        self.extensions = extensions

    @property
    def is_replayable(self) -> bool:
        return not isinstance(self.content, AsyncIterable)

    def __repr__(self) -> str:
        return (
            f"Request(method={self.method!r}, url={self.url!r}, "
            f"headers={self.headers!r})"
        )


class Response:
    __slots__ = (
        "_buffered",
        "_closed",
        "_consumed",
        "_max_response_size",
        "_on_close",
        "_stream",
        "extensions",
        "headers",
        "request",
        "status",
    )

    def __init__(
        self,
        *,
        status: int,
        headers: Headers,
        request: Request,
        extensions: ResponseExtensions,
        stream: AsyncIterable[bytes] | None = None,
        on_close: Callable[[], Awaitable[None]] | None = None,
        max_response_size: int | None = None,
    ) -> None:
        self.status = status
        self.headers = headers
        self.request = request
        self.extensions = extensions
        self._stream = stream
        self._on_close = on_close
        self._buffered: bytes | None = None
        self._consumed = False
        self._closed = False
        self._max_response_size = max_response_size

    @property
    def is_success(self) -> bool:
        return 200 <= self.status < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status < 400

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status < 600

    async def _iter_source(self) -> AsyncIterator[bytes]:
        if self._stream is None:
            return
        async for chunk in self._stream:
            yield chunk

    def _charset(self) -> str:
        content_type = self.headers.get("content-type", "") or ""
        for part in content_type.split(";")[1:]:
            name, separator, value = part.partition("=")
            if separator and name.strip().casefold() == "charset":
                return value.strip().strip("\"'") or "utf-8"
        return "utf-8"

    async def aread(self) -> bytes:
        if self._buffered is not None:
            return self._buffered
        if self._consumed:
            raise RuntimeError("response stream already consumed")

        chunks: list[bytes] = []
        total = 0
        async for chunk in self._iter_source():
            total += len(chunk)
            if self._max_response_size is not None and total > self._max_response_size:
                await self.aclose()
                raise BodyTooLargeError(
                    "response body exceeded "
                    f"max_response_size={self._max_response_size} bytes"
                )
            chunks.append(chunk)
        self._buffered = b"".join(chunks)
        self._consumed = True
        return self._buffered

    async def text(self) -> str:
        try:
            return (await self.aread()).decode(self._charset())
        except (LookupError, UnicodeDecodeError) as exc:
            raise DecodeError("response text decode failed") from exc

    async def json(self) -> Any:
        try:
            return _json.loads(await self.aread())
        except (_json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise DecodeError("response json decode failed") from exc

    async def aiter_bytes(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if self._buffered is not None:
            for offset in range(0, len(self._buffered), chunk_size):
                yield self._buffered[offset : offset + chunk_size]
            return
        if self._consumed:
            raise RuntimeError("response stream already consumed")

        self._consumed = True
        pending = bytearray()
        async for chunk in self._iter_source():
            pending.extend(chunk)
            while len(pending) >= chunk_size:
                yield bytes(pending[:chunk_size])
                del pending[:chunk_size]
        if pending:
            yield bytes(pending)

    async def aiter_lines(self) -> AsyncIterator[str]:
        try:
            decoder = codecs.getincrementaldecoder(self._charset())()
            pending = ""
            async for chunk in self.aiter_bytes():
                pending += decoder.decode(chunk)
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    yield line.removesuffix("\r")
            pending += decoder.decode(b"", final=True)
            if pending:
                yield pending.removesuffix("\r")
        except (LookupError, UnicodeDecodeError) as exc:
            raise DecodeError("response text decode failed") from exc

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            close = getattr(self._stream, "aclose", None)
            if close is not None:
                result = close()
                if inspect.isawaitable(result):
                    await result
        finally:
            if self._on_close is not None:
                await self._on_close()

    def __repr__(self) -> str:
        return f"Response(status={self.status}, url={self.request.url!r})"


@runtime_checkable
class BaseTransport(Protocol):
    async def handle(self, request: Request) -> Response: ...

    async def aclose(self) -> None: ...


type CallNext = Callable[[Request], Awaitable[Response]]


@runtime_checkable
class Middleware(Protocol):
    async def __call__(self, request: Request, call_next: CallNext) -> Response: ...


class AttemptOutcome(TypedDict):
    status: int | None
    exception: BaseException | None
    elapsed: float


@runtime_checkable
class AttemptListener(Protocol):
    def on_attempt(self, outcome: AttemptOutcome) -> None: ...


class AuthPolicy(Protocol):
    pass


__all__ = (
    "URL",
    "AttemptListener",
    "AttemptOutcome",
    "AuthPolicy",
    "BaseTransport",
    "CallNext",
    "Headers",
    "Middleware",
    "QueryValue",
    "Request",
    "RequestExtensions",
    "Response",
    "ResponseExtensions",
    "Result",
    "Timeout",
)
