from __future__ import annotations

import mimetypes
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from rapidy_client._models import Response

DEFAULT_CONTENT_TYPE = "application/octet-stream"
DEFAULT_CHUNK_SIZE = 65536

_EXTRA_TYPES: dict[str, str] = {
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".ndjson": "application/x-ndjson",
    ".md": "text/markdown",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".toml": "application/toml",
    ".webp": "image/webp",
    ".webm": "video/webm",
    ".wasm": "application/wasm",
    ".zst": "application/zstd",
    ".br": "application/x-brotli",
}


def guess_content_type(name: str | Path) -> str | None:
    suffix = Path(name).suffix.lower()
    if suffix in _EXTRA_TYPES:
        return _EXTRA_TYPES[suffix]
    guessed, _ = mimetypes.guess_type(str(name))
    return guessed


def guess_extension(content_type: str) -> str | None:
    normalized = content_type.split(";", 1)[0].strip().lower()
    for extension, candidate in _EXTRA_TYPES.items():
        if candidate == normalized:
            return extension
    return mimetypes.guess_extension(normalized)


async def aiter_file(
    path: str | Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> AsyncIterator[bytes]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    with Path(path).open("rb") as file:  # noqa: ASYNC230 - bounded chunk reads
        while chunk := file.read(chunk_size):
            yield chunk


class _StreamClient(Protocol):
    def stream(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> AbstractAsyncContextManager[Response]: ...


async def download_to(
    client: _StreamClient,
    path: str,
    dest: str | Path,
    *,
    method: str = "GET",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    **kwargs: Any,
) -> Path:
    destination = Path(dest)
    async with client.stream(method, path, **kwargs) as response:
        with destination.open("wb") as file:  # noqa: ASYNC230 - bounded writes
            async for chunk in response.aiter_bytes(chunk_size):
                file.write(chunk)
    return destination


__all__ = (
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CONTENT_TYPE",
    "aiter_file",
    "download_to",
    "guess_content_type",
    "guess_extension",
)
