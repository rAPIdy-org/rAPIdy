from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from rapidy_client._redaction import DEFAULT_REDACTOR

if TYPE_CHECKING:
    from pydantic import BaseModel

    from rapidy_client._models import Response


class HttpClientError(Exception):
    upstream: str | None
    endpoint: str | None
    request_id: str | None

    def __init__(
        self,
        *args: object,
        upstream: str | None = None,
        endpoint: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.upstream = upstream
        self.endpoint = endpoint
        self.request_id = request_id
        super().__init__(*args)

    def _context(self) -> str:
        values = (
            ("upstream", self.upstream),
            ("endpoint", self.endpoint),
            ("request_id", self.request_id),
        )
        populated = " ".join(f"{name}={value}" for name, value in values if value)
        return f" [{populated}]" if populated else ""

    def __str__(self) -> str:
        return DEFAULT_REDACTOR.redact_text(Exception.__str__(self) + self._context())

    def __repr__(self) -> str:
        args = DEFAULT_REDACTOR.redact_text(str(self.args))
        context = DEFAULT_REDACTOR.redact_text(self._context())
        return f"{type(self).__name__}({args}){context}"


class ClientClosedError(HttpClientError):
    pass


class TransportError(HttpClientError):
    pass


class ConnectError(TransportError):
    pass


class DNSResolveError(ConnectError):
    pass


class TLSError(ConnectError):
    pass


class ProxyError(TransportError):
    pass


class ServerDisconnectedError(TransportError):
    pass


class ProtocolError(TransportError):
    pass


class HttpTimeoutError(TransportError, TimeoutError):
    phase: Literal["connect", "read", "write", "pool", "total"]

    def __init__(
        self,
        *args: object,
        phase: Literal["connect", "read", "write", "pool", "total"],
        upstream: str | None = None,
        endpoint: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.phase = phase
        super().__init__(
            *args,
            upstream=upstream,
            endpoint=endpoint,
            request_id=request_id,
        )


class DeadlineExceededError(HttpClientError):
    pass


class CircuitOpenError(HttpClientError):
    retry_after_hint: float | None

    def __init__(
        self,
        *args: object,
        retry_after_hint: float | None = None,
        upstream: str | None = None,
        endpoint: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.retry_after_hint = retry_after_hint
        super().__init__(
            *args,
            upstream=upstream,
            endpoint=endpoint,
            request_id=request_id,
        )


class RedirectError(HttpClientError):
    pass


class TooManyRedirectsError(RedirectError):
    pass


class RedirectNotAllowedError(RedirectError):
    pass


class StatusError(HttpClientError):
    status: int
    response: Response
    error_model: BaseModel | None

    def __init__(
        self,
        *args: object,
        status: int,
        response: Response,
        error_model: BaseModel | None = None,
        upstream: str | None = None,
        endpoint: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.status = status
        self.response = response
        self.error_model = error_model
        super().__init__(
            *args,
            upstream=upstream,
            endpoint=endpoint,
            request_id=request_id,
        )

    def __repr__(self) -> str:
        try:
            buffered = self.response._buffered
            if buffered is None:
                body = "<unread>"
            else:
                content_type = self.response.headers.get("content-type", "") or ""
                charset = "utf-8"
                for part in content_type.split(";")[1:]:
                    name, separator, value = part.partition("=")
                    if separator and name.strip().casefold() == "charset":
                        charset = value.strip().strip("\"'") or "utf-8"
                        break
                body = buffered.decode(charset, errors="replace")
                body = DEFAULT_REDACTOR.redact_text(DEFAULT_REDACTOR.crop(body))
            url = repr(self.response.request.url)
        except Exception:  # noqa: BLE001 - repr must never mask the original error
            body = "<unavailable>"
            url = "<unavailable>"
        args = DEFAULT_REDACTOR.redact_text(str(self.args))
        context = DEFAULT_REDACTOR.redact_text(self._context())
        return (
            f"{type(self).__name__}({args}, status={self.status}, "
            f"url={url}, body={body!r}){context}"
        )


class BodyTooLargeError(HttpClientError):
    pass


class DecodeError(HttpClientError):
    pass


class ResponseValidationError(HttpClientError):
    pass


class WSError(HttpClientError):
    pass


class WSHandshakeError(WSError):
    status: int | None

    def __init__(
        self,
        *args: object,
        status: int | None = None,
        upstream: str | None = None,
        endpoint: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.status = status
        super().__init__(
            *args,
            upstream=upstream,
            endpoint=endpoint,
            request_id=request_id,
        )


class WSClosedError(WSError):
    code: int | None
    reason: str | None

    def __init__(
        self,
        *args: object,
        code: int | None = None,
        reason: str | None = None,
        upstream: str | None = None,
        endpoint: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.code = code
        self.reason = reason
        super().__init__(
            *args,
            upstream=upstream,
            endpoint=endpoint,
            request_id=request_id,
        )


class WSQueueFullError(WSError):
    pass


class MessageValidationError(HttpClientError):
    pass


class SchemaDefinitionError(Exception):
    pass


__all__ = (
    "BodyTooLargeError",
    "CircuitOpenError",
    "ClientClosedError",
    "ConnectError",
    "DNSResolveError",
    "DeadlineExceededError",
    "DecodeError",
    "HttpClientError",
    "HttpTimeoutError",
    "MessageValidationError",
    "ProtocolError",
    "ProxyError",
    "RedirectError",
    "RedirectNotAllowedError",
    "ResponseValidationError",
    "SchemaDefinitionError",
    "ServerDisconnectedError",
    "StatusError",
    "TLSError",
    "TooManyRedirectsError",
    "TransportError",
    "WSClosedError",
    "WSError",
    "WSHandshakeError",
    "WSQueueFullError",
)
