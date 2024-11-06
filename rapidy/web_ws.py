from aiohttp import WSMsgType
from aiohttp.web_ws import WebSocketResponse, WebSocketReady

__all__ = (
    'WebSocketResponse',  # TODO: переработать
    'WebSocketReady',
    'WSMsgType',
    'WSData',
)

from rapidy._field_info import RapidyFieldInfo


class WSData(RapidyFieldInfo):
    pass
