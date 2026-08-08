import threading

container = make_container(provider, lock_factory=threading.Lock):
with container(lock_factory=threading.Lock) as nested_container:
    ...

import asyncio

container = make_async_container(provider, lock_factory=asyncio.Lock)
async with container(lock_factory=asyncio.Lock) as nested_container:
    ...
