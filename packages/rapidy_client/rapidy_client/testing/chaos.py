from __future__ import annotations

import asyncio
import socket
import struct
from types import TracebackType
from typing import Literal, Self

_Scenario = Literal[
    "ok",
    "freeze",
    "disconnect_after",
    "reset_on_reuse",
    "slow_body",
    "ws_drop_every",
    "retry_after",
    "stall_request_read",
]

_REASONS = {
    200: "OK",
    201: "Created",
    204: "No Content",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


class ChaosServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._configured_port = port
        self._bound_port = port
        self._server: asyncio.AbstractServer | None = None
        self._writers: set[asyncio.StreamWriter] = set()
        self._tasks: set[asyncio.Task[None]] = set()
        self._scenario: _Scenario = "ok"
        self._status = 200
        self._body = b""
        self._headers: dict[str, str] = {}
        self._seconds = 0.0
        self._n_bytes = 0
        self._bytes_per_sec = 1
        self._drop_every = 1

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._bound_port

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def start(self) -> None:
        if self._server is not None:
            return
        self._server = await asyncio.start_server(
            self._handle_conn,
            self._host,
            self._configured_port,
        )
        sockets = self._server.sockets
        if not sockets:
            raise RuntimeError("ChaosServer started without a listening socket")
        self._bound_port = int(sockets[0].getsockname()[1])

    async def stop(self) -> None:
        server = self._server
        if server is None:
            return
        self._server = None
        server.close()
        await server.wait_closed()

        for writer in tuple(self._writers):
            writer.close()
        for task in tuple(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
        self._writers.clear()
        self._tasks.clear()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        del exc_type, exc, tb
        await self.stop()

    def respond_ok(
        self,
        *,
        status: int = 200,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> Self:
        self._scenario = "ok"
        self._status = status
        self._body = body
        self._headers = dict(headers or {})
        return self

    def freeze(self, seconds: float) -> Self:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        self._scenario = "freeze"
        self._seconds = seconds
        return self

    def disconnect_after(self, n_bytes: int) -> Self:
        if n_bytes < 0:
            raise ValueError("n_bytes must be non-negative")
        self._scenario = "disconnect_after"
        self._n_bytes = n_bytes
        return self

    def reset_on_reuse(self) -> Self:
        self._scenario = "reset_on_reuse"
        return self

    def slow_body(self, bytes_per_sec: int) -> Self:
        if bytes_per_sec <= 0:
            raise ValueError("bytes_per_sec must be greater than zero")
        self._scenario = "slow_body"
        self._bytes_per_sec = bytes_per_sec
        self._body = b"x" * bytes_per_sec
        return self

    def ws_drop_every(self, n: int) -> Self:
        if n <= 0:
            raise ValueError("n must be greater than zero")
        self._scenario = "ws_drop_every"
        self._drop_every = n
        return self

    def retry_after(self, value: str | int, *, status: int = 503) -> Self:
        self._scenario = "retry_after"
        self._status = status
        self._body = b"retry later"
        self._headers = {"Retry-After": str(value)}
        return self

    def stall_request_read(self, seconds: float) -> Self:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        self._scenario = "stall_request_read"
        self._seconds = seconds
        return self

    async def _read_headers(
        self, reader: asyncio.StreamReader
    ) -> tuple[bytes, int] | None:
        try:
            data = await reader.readuntil(b"\r\n\r\n")
        except (asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            return None
        content_length = 0
        for line in data.split(b"\r\n")[1:]:
            name, separator, value = line.partition(b":")
            if separator and name.strip().lower() == b"content-length":
                try:
                    content_length = int(value.strip())
                except ValueError:
                    content_length = 0
                break
        return data, content_length

    async def _drain_request_body(
        self,
        reader: asyncio.StreamReader,
        content_length: int,
    ) -> None:
        if content_length:
            await reader.readexactly(content_length)

    def _response_head(
        self,
        *,
        status: int,
        content_length: int,
        headers: dict[str, str] | None = None,
    ) -> bytes:
        reason = _REASONS.get(status, "Status")
        lines = [
            f"HTTP/1.1 {status} {reason}",
            f"Content-Length: {content_length}",
            "Connection: keep-alive",
            "Server: chaos",
        ]
        for name, value in (headers or {}).items():
            if "\r" in name or "\n" in name or "\r" in value or "\n" in value:
                raise ValueError("HTTP header names and values cannot contain CR/LF")
            lines.append(f"{name}: {value}")
        return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        *,
        status: int | None = None,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        response_body = self._body if body is None else body
        response_status = self._status if status is None else status
        response_headers = self._headers if headers is None else headers
        writer.write(
            self._response_head(
                status=response_status,
                content_length=len(response_body),
                headers=response_headers,
            )
            + response_body
        )
        await writer.drain()

    async def _send_slow_body(self, writer: asyncio.StreamWriter) -> None:
        writer.write(self._response_head(status=200, content_length=len(self._body)))
        await writer.drain()
        chunk_size = max(1, self._bytes_per_sec // 10)
        for offset in range(0, len(self._body), chunk_size):
            chunk = self._body[offset : offset + chunk_size]
            writer.write(chunk)
            await writer.drain()
            if offset + len(chunk) < len(self._body):
                await asyncio.sleep(len(chunk) / self._bytes_per_sec)

    def _abort(self, writer: asyncio.StreamWriter) -> None:
        raw_socket = writer.get_extra_info("socket")
        if raw_socket is not None:
            try:
                raw_socket.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_LINGER,
                    struct.pack("ii", 1, 0),
                )
            except OSError:
                pass
        writer.transport.abort()

    async def _handle_conn(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._tasks.add(task)
        self._writers.add(writer)
        request_count = 0
        try:
            while True:
                parsed = await self._read_headers(reader)
                if parsed is None:
                    return
                _, content_length = parsed
                request_count += 1

                if self._scenario == "stall_request_read":
                    await asyncio.sleep(self._seconds)
                    return
                await self._drain_request_body(reader, content_length)

                if self._scenario == "freeze":
                    await asyncio.sleep(self._seconds)
                    return
                if self._scenario == "disconnect_after":
                    writer.write(
                        self._response_head(
                            status=200,
                            content_length=self._n_bytes + 1,
                        )
                        + b"x" * self._n_bytes
                    )
                    await writer.drain()
                    return
                if self._scenario == "reset_on_reuse" and request_count > 1:
                    self._abort(writer)
                    return
                if (
                    self._scenario == "ws_drop_every"
                    and request_count % self._drop_every == 0
                ):
                    self._abort(writer)
                    return
                if self._scenario == "slow_body":
                    await self._send_slow_body(writer)
                else:
                    await self._send_response(writer)
        except (
            asyncio.CancelledError,
            asyncio.IncompleteReadError,
            ConnectionError,
            OSError,
        ):
            return
        finally:
            self._writers.discard(writer)
            if task is not None:
                self._tasks.discard(task)
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass


__all__ = ("ChaosServer",)
