from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Self

import httpx

from rapidy import Rapidy

type ASGIMessage = dict[str, Any]
type AppClientFactory = Callable[[Rapidy], Awaitable['AppClient']]


class LifespanRunner:
    """Drive one application's ASGI lifespan alongside HTTPX's ASGI transport."""

    def __init__(self, app: Rapidy) -> None:
        self._app = app
        self._incoming: asyncio.Queue[ASGIMessage] = asyncio.Queue()
        self._outgoing: asyncio.Queue[ASGIMessage] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._task = asyncio.create_task(
            self._app({'type': 'lifespan'}, self._incoming.get, self._outgoing.put)
        )
        await self._incoming.put({'type': 'lifespan.startup'})
        message = await self._outgoing.get()
        if message.get('type') == 'lifespan.startup.failed':
            await self._wait_for_task()
            msg = str(message.get('message', 'Application startup failed'))
            raise RuntimeError(msg)
        if message.get('type') != 'lifespan.startup.complete':
            msg = f'Unexpected lifespan startup message: {message!r}'
            raise RuntimeError(msg)
        self._started = True

    async def close(self) -> None:
        if not self._started:
            if self._task is not None:
                await self._wait_for_task()
            return
        self._started = False
        await self._incoming.put({'type': 'lifespan.shutdown'})
        message = await self._outgoing.get()
        if message.get('type') == 'lifespan.shutdown.failed':
            await self._wait_for_task()
            msg = str(message.get('message', 'Application shutdown failed'))
            raise RuntimeError(msg)
        if message.get('type') != 'lifespan.shutdown.complete':
            msg = f'Unexpected lifespan shutdown message: {message!r}'
            raise RuntimeError(msg)
        await self._wait_for_task()

    async def _wait_for_task(self) -> None:
        if self._task is not None:
            task, self._task = self._task, None
            await task


class ClientResponse:
    """Small aiohttp-compatible response adapter over ``httpx.Response``."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    @property
    def status(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> Mapping[str, str]:
        return self._response.headers

    async def text(self) -> str:
        return self._response.text

    async def json(self) -> Any:
        return self._response.json()

    async def read(self) -> bytes:
        return self._response.content


class AppClient:
    """Lifespan-aware in-process client for a ``Rapidy`` ASGI application."""

    def __init__(self, app: Rapidy, lifespan: LifespanRunner, client: httpx.AsyncClient) -> None:
        self.app = app
        self._lifespan = lifespan
        self._client = client
        self._closed = False

    @classmethod
    async def create(cls, app: Rapidy) -> Self:
        lifespan = LifespanRunner(app)
        await lifespan.start()
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url='http://testserver')
        return cls(app, lifespan, client)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        await self._client.aclose()
        await self._lifespan.close()

    async def request(self, method: str, path: str, **kwargs: Any) -> ClientResponse:
        if 'allow_redirects' in kwargs:
            kwargs['follow_redirects'] = kwargs.pop('allow_redirects')
        data = kwargs.get('data')
        if isinstance(data, (bytes, str)) and 'files' not in kwargs:
            kwargs['content'] = kwargs.pop('data')
            if isinstance(data, str):
                headers = dict(kwargs.get('headers') or {})
                if not any(name.lower() == 'content-type' for name in headers):
                    headers['Content-Type'] = 'text/plain; charset=utf-8'
                kwargs['headers'] = headers
        cookies = kwargs.get('cookies')
        if isinstance(cookies, dict):
            kwargs['cookies'] = {name: str(value) for name, value in cookies.items()}
        response = await self._client.request(method, path, **kwargs)
        return ClientResponse(response)

    async def get(self, path: str, **kwargs: Any) -> ClientResponse:
        return await self.request('GET', path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> ClientResponse:
        return await self.request('POST', path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> ClientResponse:
        return await self.request('PUT', path, **kwargs)

    async def patch(self, path: str, **kwargs: Any) -> ClientResponse:
        return await self.request('PATCH', path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> ClientResponse:
        return await self.request('DELETE', path, **kwargs)

    async def head(self, path: str, **kwargs: Any) -> ClientResponse:
        return await self.request('HEAD', path, **kwargs)

    async def options(self, path: str, **kwargs: Any) -> ClientResponse:
        return await self.request('OPTIONS', path, **kwargs)
