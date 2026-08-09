from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import cast, TYPE_CHECKING

from rapidy.exceptions import HTTPNotFound, HTTPTemporaryRedirect
from rapidy.middlewares._utils import external_path
from rapidy.request import Request
from rapidy.responses.files import FileResponse
from rapidy.routing.http.base import BaseHTTPRouter
from rapidy.typedefs import TerminalHandler

if TYPE_CHECKING:
    from rapidy.application import Rapidy

__all__ = ('StaticFiles',)


class StaticFiles(BaseHTTPRouter):
    """Register a safe GET/HEAD file tree under one route prefix."""

    __slots__ = (
        '_cache_control',
        '_directory',
        '_follow_symlinks',
        '_html',
        '_index_file',
        '_public',
    )

    def __init__(
        self,
        path: str,
        *,
        directory: str | Path,
        html: bool = False,
        index_file: str = 'index.html',
        follow_symlinks: bool = False,
        cache_control: str | None = 'public, max-age=3600',
        public: bool = True,
    ) -> None:
        normalized_path = path.rstrip('/') or '/'
        super().__init__(path)
        self.path = normalized_path
        prefix_parts = normalized_path.split('/')
        if any(character in normalized_path for character in ('{', '}', '\\', '\x00', '\r', '\n')) or any(
            part in {'.', '..'} for part in prefix_parts
        ):
            msg = 'Static route path must be a literal URL prefix'
            raise ValueError(msg)
        try:
            directory_path = Path(directory).expanduser().resolve(strict=True)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            msg = f'Static directory is not accessible: {directory!s}'
            raise ValueError(msg) from exc
        if not directory_path.is_dir():
            msg = f'Static directory is not a directory: {directory!s}'
            raise ValueError(msg)
        if not index_file or '/' in index_file or '\\' in index_file or index_file in {'.', '..'}:
            msg = 'index_file must be one file name'
            raise ValueError(msg)
        if cache_control is not None and any(character in cache_control for character in ('\x00', '\r', '\n')):
            msg = 'cache_control must not contain control characters'
            raise ValueError(msg)
        self._directory = directory_path
        self._html = html
        self._index_file = index_file
        self._follow_symlinks = follow_symlinks
        self._cache_control = cache_control
        self._public = public

    @property
    def directory(self) -> Path:
        """Return the resolved static root."""
        return self._directory

    def route_register(self, application: Rapidy) -> None:
        """Register static root and recursive GET/HEAD routes."""
        root = cast('str', self.path)
        child = f'{root.rstrip("/")}/{{path:.*}}' if root != '/' else '/{path:.*}'
        metadata = {'include_in_schema': False, 'public': self._public}
        terminal = cast('TerminalHandler', self._serve)
        application._matcher.add_route(  # noqa: SLF001
            'GET',
            root,
            terminal,
            metadata,
            handler=cast('TerminalHandler', self._serve),
        )
        application._matcher.add_route(  # noqa: SLF001
            'GET',
            child,
            terminal,
            metadata,
            handler=cast('TerminalHandler', self._serve),
        )

    async def _serve(self, request: Request) -> FileResponse:
        relative_path = request.path_params.get('path', '')
        candidate = self._resolve_candidate(relative_path)
        if candidate.is_dir():
            if not self._html:
                raise HTTPNotFound
            index = self._safe_child(candidate, self._index_file)
            if not index.is_file():
                raise HTTPNotFound
            if not external_path(request).endswith('/'):
                location = f'{external_path(request)}/'
                query = request.scope.get('query_string', b'')
                if isinstance(query, bytes) and query:
                    location = f'{location}?{query.decode("latin-1")}'
                raise HTTPTemporaryRedirect(location)
            candidate = index
        if not candidate.is_file():
            raise HTTPNotFound

        headers = {'Cache-Control': self._cache_control} if self._cache_control is not None else None
        return FileResponse(candidate, headers=headers)

    def _resolve_candidate(self, value: str) -> Path:
        if '\x00' in value or '\\' in value:
            raise HTTPNotFound
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {'.', '..'} for part in path.parts):
            raise HTTPNotFound
        current = self._directory
        for part in path.parts:
            current /= part
            if not self._follow_symlinks and current.is_symlink():
                raise HTTPNotFound
        try:
            resolved = current.resolve(strict=False)
            resolved.relative_to(self._directory)
        except (OSError, ValueError) as exc:
            raise HTTPNotFound from exc
        return resolved

    def _safe_child(self, directory: Path, name: str) -> Path:
        candidate = directory / name
        if not self._follow_symlinks and candidate.is_symlink():
            raise HTTPNotFound
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(self._directory)
        except (OSError, ValueError) as exc:
            raise HTTPNotFound from exc
        return resolved
