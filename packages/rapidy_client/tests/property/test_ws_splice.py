from __future__ import annotations

from itertools import pairwise

from hypothesis import given, settings
from hypothesis import strategies as st
from rapidy_client import (
    UNSET,
    URL,
    Headers,
    HttpClient,
    RedirectConfig,
    Request,
    RequestExtensions,
    Timeout,
    UpstreamConfig,
)
from rapidy_client.testing import MockTransport
from rapidy_client.ws import Heartbeat, WSMessage, WSSession
from wsproto import ConnectionType
from wsproto.connection import Connection
from wsproto.events import BytesMessage, TextMessage


class _NullStream:
    async def read(self, max_bytes: int = 65536) -> bytes:
        del max_bytes
        return b""

    async def write(self, data: bytes) -> None:
        del data

    async def aclose(self) -> None:
        return None


def _session() -> WSSession[object, object]:
    client = HttpClient(
        UpstreamConfig(base_url="https://mock.test"),
        transport=MockTransport(),
    )
    request = Request(
        method="GET",
        url=URL("wss://mock.test/events"),
        headers=Headers(),
        content=None,
        extensions=RequestExtensions(
            upstream="ws-property",
            endpoint="/events",
            request_id=None,
            timeout=Timeout(),
            retry=None,
            idempotent=True,
            auth_override=UNSET,
            deadline=None,
            redirects=RedirectConfig(),
        ),
    )
    return WSSession(
        _stream=_NullStream(),
        _client=client,
        _request=request,
        _heartbeat=Heartbeat(),
        _send_queue_limit=1,
        _send_timeout=1.0,
        _subprotocol=None,
    )


def _decode(frame: bytes, offsets: list[int]) -> WSMessage:
    session = _session()
    points = [0, *sorted(set(offsets)), len(frame)]
    for start, end in pairwise(points):
        if start == end:
            continue
        session._connection.receive_data(frame[start:end])
        for event in session._connection.events():
            if isinstance(event, (TextMessage, BytesMessage)):
                session._message_event(event)
    item = session._receive_queue.get_nowait()
    assert isinstance(item, WSMessage)
    return item


@settings(max_examples=40, deadline=None)
@given(
    payload=st.one_of(
        st.text(alphabet=st.characters(blacklist_categories=("Cs",))),
        st.binary(),
    ),
    offsets=st.lists(st.integers(min_value=0, max_value=4096), max_size=20),
)
def test_ws_frame_splice_invariant(payload: str | bytes, offsets: list[int]) -> None:
    server = Connection(ConnectionType.SERVER)
    event = (
        TextMessage(data=payload)
        if isinstance(payload, str)
        else BytesMessage(data=payload)
    )
    frame = server.send(event)
    bounded_offsets = [min(offset, len(frame)) for offset in offsets]

    spliced = _decode(frame, bounded_offsets)
    whole = _decode(frame, [])

    assert spliced == whole
    if isinstance(payload, str):
        assert spliced == WSMessage(kind="text", text=payload, data=None)
    else:
        assert spliced == WSMessage(kind="binary", text=None, data=payload)
