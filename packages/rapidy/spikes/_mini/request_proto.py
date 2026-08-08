from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from multidict import CIMultiDict, CIMultiDictProxy


class Request:
    def __init__(self, scope: dict[str, Any], receive: Any) -> None:
        self.scope = scope
        self.receive = receive
        self.method = str(scope.get("method", "GET")).upper()
        self.path = str(scope.get("path", "/"))
        self.path_params: dict[str, str] = dict(scope.get("path_params", {}))
        self.headers = CIMultiDictProxy(
            CIMultiDict(
                (key.decode("latin-1"), value.decode("latin-1"))
                for key, value in scope.get("headers", [])
            ),
        )
        self.state = SimpleNamespace()


__all__ = ("Request",)
