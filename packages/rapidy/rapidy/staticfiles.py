from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, cast

from rapidy import application as _application
from rapidy.exceptions import HTTPNotFound, HTTPTemporaryRedirect
from rapidy.middlewares._utils import external_path
from rapidy.request import Request
from rapidy.responses.files import FileResponse
from rapidy.routing.http.base import BaseHTTPRouter
from rapidy.typedefs import TerminalHandler

__all__ = ('StaticFiles',)


class StaticFiles(BaseHTTPRouter):
    """Register a safe GET/HEAD file tree under one route prefix."""

    __slots__ = (
        '_allow_dotfiles',
        '_cache_control',
        '_directory',
        '_follow_symlinks',
        '_html',
        '_index_file',
        '_name',
        '_public',
    )

    def __init__(
        self,
        path: str,
        *,
        directory: str | Path,
        name: str | None = None,
        html: bool = False,
        index_file: str = 'index.html',
        follow_symlinks: bool = False,
        allow_dotfiles: bool = False,
        cache_control: str | None = 'public, max-age=3600',
        public: bool = False,
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
        if index_file.startswith('.') and not allow_dotfiles:
            msg = 'A dotfile index requires allow_dotfiles=True'
            raise ValueError(msg)
        if cache_control is not None and any(character in cache_control for character in ('\x00', '\r', '\n')):
            msg = 'cache_control must not contain control characters'
            raise ValueError(msg)
        self._directory = directory_path
        if name is not None and (not isinstance(name, str) or not name):
            msg = 'Static route name must be a non-empty string'
            raise ValueError(msg)
        self._name = name
        self._html = html
        self._index_file = index_file
        self._follow_symlinks = follow_symlinks
        self._allow_dotfiles = allow_dotfiles
        self._cache_control = cache_control
        self._public = public

    @property
    def directory(self) -> Path:
        """Return the resolved static root."""
        return self._directory

    def route_register(self, application: _application.Rapidy) -> None:
        """Register static root and recursive GET/HEAD routes."""
        root = cast('str', self.path)
        child = f'{root.rstrip("/")}/{{path:.*}}' if root != '/' else '/{path:.*}'
        metadata: dict[str, Any] = {'include_in_schema': False, 'public': self._public}
        root_metadata = dict(metadata)
        if self._name is not None:
            metadata['name'] = self._name
            root_metadata['name'] = f'{self._name}:index'
        terminal = cast('TerminalHandler', self._serve)
        application._matcher.add_route(  # noqa: SLF001
            'GET',
            root,
            terminal,
            root_metadata,
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
        return FileResponse(
            candidate,
            headers=headers,
            _opener=lambda: _open_static_candidate(self._directory, candidate),
        )

    def _resolve_candidate(self, value: str) -> Path:
        if '\x00' in value or '\\' in value:
            raise HTTPNotFound
        path = PurePosixPath(value)
        if path.is_absolute() or any(
            part in {'.', '..'} or (part.startswith('.') and not self._allow_dotfiles) for part in path.parts
        ):
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


def _open_static_candidate(root: Path, candidate: Path) -> BinaryIO:
    relative = candidate.relative_to(root)
    if not relative.parts:
        raise IsADirectoryError(candidate)
    if (
        os.open in os.supports_dir_fd
        and hasattr(os, 'O_DIRECTORY')
        and hasattr(os, 'O_NOFOLLOW')
    ):
        return _open_static_candidate_at(root, relative.parts)
    return _open_static_candidate_portable(root, candidate)


def _open_static_candidate_at(root: Path, parts: tuple[str, ...]) -> BinaryIO:
    base_flags = os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | os.O_NOFOLLOW
    directory_flags = base_flags | os.O_DIRECTORY
    current_fd = os.open(root, directory_flags)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(parts[-1], base_flags, dir_fd=current_fd)
    finally:
        os.close(current_fd)
    return os.fdopen(file_fd, 'rb')


def _open_static_candidate_portable(root: Path, candidate: Path) -> BinaryIO:
    file_object = candidate.open('rb')
    try:
        opened_stat = os.fstat(file_object.fileno())
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
        current_stat = resolved.stat()
        if (opened_stat.st_dev, opened_stat.st_ino) != (current_stat.st_dev, current_stat.st_ino):
            raise FileNotFoundError(candidate)
    except (OSError, ValueError):
        file_object.close()
        raise
    return file_object
