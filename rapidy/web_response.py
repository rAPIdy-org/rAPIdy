import json
from typing import Any, Optional

from aiohttp.abc import AbstractStreamWriter
from aiohttp.helpers import sentinel
from aiohttp.web_request import BaseRequest
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
    async def _start(self, request: BaseRequest) -> AbstractStreamWriter:
        self._req = request
        writer = self._payload_writer = request._payload_writer  # noqa: WPS429

        try:
            server_info_in_response = request.app._server_info_in_response
        except AttributeError:  # note: just in case
            # It is hidden by default, as I believe showing server information is a potential vulnerability.
            server_info_in_response = False

        await self._ext_prepare_headers(server_info_in_response=server_info_in_response)
        await request._prepare_hook(self)
        await self._write_headers()

        return writer

    async def _ext_prepare_headers(self, server_info_in_response: bool) -> None:
        await super()._prepare_headers()  # noqa: WPS613

        if not server_info_in_response:  # noqa: WPS504
            self._headers.pop(hdrs.SERVER)
        else:
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
