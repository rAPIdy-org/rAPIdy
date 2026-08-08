from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import Any, cast, TYPE_CHECKING

from multidict import CIMultiDict

from rapidy.typedefs import ASGIScope, Receive

if TYPE_CHECKING:
    from rapidy.application import Rapidy

__all__ = ('BaseRequest', 'Request', 'State')


class State(MutableMapping[str, Any]):
    """One string-keyed store with mapping and attribute access."""

    __slots__ = ('_data',)

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, '_data', data if data is not None else {})

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getattr__(self, key: str) -> Any:
        try:
            return self._data[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self._data[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


class Request:
    """Minimal request view over an HTTP ASGI scope."""

    __slots__ = (
        '_receive',
        'app',
        'headers',
        'method',
        'path',
        'path_params',
        'scope',
        'state',
    )

    def __init__(self, scope: ASGIScope, receive: Receive) -> None:
        self.scope = scope
        self._receive = receive
        self.method = str(scope['method']).upper()
        self.path = str(scope['path'])
        self.path_params = dict(cast('dict[str, str]', scope.get('path_params', {})))
        self.headers: CIMultiDict[str] = CIMultiDict(
            (bytes(name).decode('latin-1'), bytes(value).decode('latin-1'))
            for name, value in cast('list[tuple[bytes, bytes]]', scope.get('headers', []))
        )
        raw_state = cast('dict[str, Any]', scope.setdefault('state', {}))
        self.state = State(raw_state)
        self.app = cast('Rapidy', scope['app'])


BaseRequest = Request
