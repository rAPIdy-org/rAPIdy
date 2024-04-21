import json
from typing import Any, Optional

from aiohttp.helpers import sentinel
from aiohttp.web_response import ContentCoding, Response as _AioHTTPResponse, StreamResponse as _AioHTTPStreamResponse

from rapidy import hdrs
from rapidy._version import SERVER_INFO
from rapidy.typedefs import JSONEncoder, LooseHeaders

__all__ = (
    'ContentCoding',
    'StreamResponse',
    'Response',
    'json_response',
)


class SpecifyBothTextAndBodyError(ValueError):
    _base_err_msg = '`json_response` cannot be created - only one of `data`, `text`, or `body` should be specified'

    def __init__(self, *args: Any) -> None:
        super().__init__(self._base_err_msg, *args)


class StreamResponse(_AioHTTPStreamResponse):
    async def _prepare_headers(self) -> None:
        await super()._prepare_headers()
        self._headers[hdrs.SERVER] = SERVER_INFO


class Response(_AioHTTPResponse, StreamResponse):
    pass


def json_response(
    data: Any = sentinel,
    *,
    text: Optional[str] = None,
    body: Optional[bytes] = None,
    status: int = 200,
    reason: Optional[str] = None,
    headers: Optional[LooseHeaders] = None,
    content_type: str = 'application/json',
    dumps: JSONEncoder = json.dumps,
) -> Response:
    if data is not sentinel:
        if text or body:
            raise SpecifyBothTextAndBodyError
        else:
            text = dumps(data)
    return Response(
        text=text,
        body=body,
        status=status,
        reason=reason,
        headers=headers,
        content_type=content_type,
    )
