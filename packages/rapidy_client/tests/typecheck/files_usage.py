from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import assert_type

from rapidy_client import (
    ContentFactory,
    FilePart,
    HttpClient,
    aiter_file,
    download_to,
    guess_extension,
)


async def check(client: HttpClient, path: Path) -> None:
    source = aiter_file(path)
    replayable = ContentFactory(lambda: aiter_file(path))
    part = FilePart(name="document", path=path)

    assert_type(source, AsyncIterator[bytes])
    assert_type(replayable, ContentFactory)
    assert_type(part, FilePart)
    assert_type(await download_to(client, "/document", path), Path)
    assert_type(guess_extension("application/pdf"), str | None)
