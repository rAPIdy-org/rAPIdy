__version__ = '0.2.1'

from typing import Tuple, TYPE_CHECKING

from aiohttp.client import (
    BaseConnector as BaseConnector,
    ClientConnectionError as ClientConnectionError,
    ClientConnectorCertificateError as ClientConnectorCertificateError,
    ClientConnectorError as ClientConnectorError,
    ClientConnectorSSLError as ClientConnectorSSLError,
    ClientError as ClientError,
    ClientHttpProxyError as ClientHttpProxyError,
    ClientOSError as ClientOSError,
    ClientPayloadError as ClientPayloadError,
    ClientProxyConnectionError as ClientProxyConnectionError,
    ClientRequest as ClientRequest,
    ClientResponse as ClientResponse,
    ClientResponseError as ClientResponseError,
    ClientSession as ClientSession,
    ClientSSLError as ClientSSLError,
    ClientTimeout as ClientTimeout,
    ClientWebSocketResponse as ClientWebSocketResponse,
    ContentTypeError as ContentTypeError,
    Fingerprint as Fingerprint,
    InvalidURL as InvalidURL,
    NamedPipeConnector as NamedPipeConnector,
    request as request,
    RequestInfo as RequestInfo,
    ServerConnectionError as ServerConnectionError,
    ServerDisconnectedError as ServerDisconnectedError,
    ServerFingerprintMismatch as ServerFingerprintMismatch,
    ServerTimeoutError as ServerTimeoutError,
    TCPConnector as TCPConnector,
    TooManyRedirects as TooManyRedirects,
    UnixConnector as UnixConnector,
    WSServerHandshakeError as WSServerHandshakeError,
)
from aiohttp.cookiejar import CookieJar as CookieJar, DummyCookieJar as DummyCookieJar
from aiohttp.formdata import FormData as FormData
from aiohttp.helpers import BasicAuth, ChainMapProxy, ETag
from aiohttp.http import (
    HttpVersion as HttpVersion,
    HttpVersion10 as HttpVersion10,
    HttpVersion11 as HttpVersion11,
    WebSocketError as WebSocketError,
    WSCloseCode as WSCloseCode,
    WSMessage as WSMessage,
    WSMsgType as WSMsgType,
)
from aiohttp.multipart import (
    BadContentDispositionHeader as BadContentDispositionHeader,
    BadContentDispositionParam as BadContentDispositionParam,
    BodyPartReader as BodyPartReader,
    content_disposition_filename as content_disposition_filename,
    MultipartReader as MultipartReader,
    MultipartWriter as MultipartWriter,
    parse_content_disposition as parse_content_disposition,
)
from aiohttp.payload import (
    AsyncIterablePayload as AsyncIterablePayload,
    BufferedReaderPayload as BufferedReaderPayload,
    BytesIOPayload as BytesIOPayload,
    BytesPayload as BytesPayload,
    get_payload as get_payload,
    IOBasePayload as IOBasePayload,
    JsonPayload as JsonPayload,
    Payload as Payload,
    PAYLOAD_REGISTRY as PAYLOAD_REGISTRY,
    payload_type as payload_type,
    StringIOPayload as StringIOPayload,
    StringPayload as StringPayload,
    TextIOPayload as TextIOPayload,
)
from aiohttp.payload_streamer import streamer as streamer
from aiohttp.resolver import (
    AsyncResolver as AsyncResolver,
    DefaultResolver as DefaultResolver,
    ThreadedResolver as ThreadedResolver,
)
from aiohttp.tracing import (
    TraceConfig as TraceConfig,
    TraceConnectionCreateEndParams as TraceConnectionCreateEndParams,
    TraceConnectionCreateStartParams as TraceConnectionCreateStartParams,
    TraceConnectionQueuedEndParams as TraceConnectionQueuedEndParams,
    TraceConnectionQueuedStartParams as TraceConnectionQueuedStartParams,
    TraceConnectionReuseconnParams as TraceConnectionReuseconnParams,
    TraceDnsCacheHitParams as TraceDnsCacheHitParams,
    TraceDnsCacheMissParams as TraceDnsCacheMissParams,
    TraceDnsResolveHostEndParams as TraceDnsResolveHostEndParams,
    TraceDnsResolveHostStartParams as TraceDnsResolveHostStartParams,
    TraceRequestChunkSentParams as TraceRequestChunkSentParams,
    TraceRequestEndParams as TraceRequestEndParams,
    TraceRequestExceptionParams as TraceRequestExceptionParams,
    TraceRequestRedirectParams as TraceRequestRedirectParams,
    TraceRequestStartParams as TraceRequestStartParams,
    TraceResponseChunkReceivedParams as TraceResponseChunkReceivedParams,
)

from rapidy import hdrs as hdrs
from rapidy.streams import (
    DataQueue as DataQueue,
    EMPTY_PAYLOAD as EMPTY_PAYLOAD,
    EofStream as EofStream,
    FlowControlDataQueue as FlowControlDataQueue,
    StreamReader as StreamReader,
)

if TYPE_CHECKING:
    # ty aiohttp for this code <3
    # At runtime these are lazy-loaded at the bottom of the file.
    from aiohttp.worker import GunicornUVLoopWebWorker, GunicornWebWorker


__all__: Tuple[str, ...] = (
    '__version__',
    'hdrs',
    # client
    'BaseConnector',
    'ClientConnectionError',
    'ClientConnectorCertificateError',
    'ClientConnectorError',
    'ClientConnectorSSLError',
    'ClientError',
    'ClientHttpProxyError',
    'ClientOSError',
    'ClientPayloadError',
    'ClientProxyConnectionError',
    'ClientResponse',
    'ClientRequest',
    'ClientResponseError',
    'ClientSSLError',
    'ClientSession',
    'ClientTimeout',
    'ClientWebSocketResponse',
    'ContentTypeError',
    'Fingerprint',
    'InvalidURL',
    'RequestInfo',
    'ServerConnectionError',
    'ServerDisconnectedError',
    'ServerFingerprintMismatch',
    'ServerTimeoutError',
    'TCPConnector',
    'TooManyRedirects',
    'UnixConnector',
    'NamedPipeConnector',
    'WSServerHandshakeError',
    'request',
    # cookiejar
    'CookieJar',
    'DummyCookieJar',
    # formdata
    'FormData',
    # helpers
    'BasicAuth',
    'ChainMapProxy',
    'ETag',
    # http
    'HttpVersion',
    'HttpVersion10',
    'HttpVersion11',
    'WSMsgType',
    'WSCloseCode',
    'WSMessage',
    'WebSocketError',
    # multipart
    'BadContentDispositionHeader',
    'BadContentDispositionParam',
    'BodyPartReader',
    'MultipartReader',
    'MultipartWriter',
    'content_disposition_filename',
    'parse_content_disposition',
    # payload
    'AsyncIterablePayload',
    'BufferedReaderPayload',
    'BytesIOPayload',
    'BytesPayload',
    'IOBasePayload',
    'JsonPayload',
    'PAYLOAD_REGISTRY',
    'Payload',
    'StringIOPayload',
    'StringPayload',
    'TextIOPayload',
    'get_payload',
    'payload_type',
    # payload_streamer
    'streamer',
    # resolver
    'AsyncResolver',
    'DefaultResolver',
    'ThreadedResolver',
    # streams
    'DataQueue',
    'EMPTY_PAYLOAD',
    'EofStream',
    'FlowControlDataQueue',
    'StreamReader',
    # tracing
    'TraceConfig',
    'TraceConnectionCreateEndParams',
    'TraceConnectionCreateStartParams',
    'TraceConnectionQueuedEndParams',
    'TraceConnectionQueuedStartParams',
    'TraceConnectionReuseconnParams',
    'TraceDnsCacheHitParams',
    'TraceDnsCacheMissParams',
    'TraceDnsResolveHostEndParams',
    'TraceDnsResolveHostStartParams',
    'TraceRequestChunkSentParams',
    'TraceRequestEndParams',
    'TraceRequestExceptionParams',
    'TraceRequestRedirectParams',
    'TraceRequestStartParams',
    'TraceResponseChunkReceivedParams',
    # workers (imported lazily with __getattr__)
    'GunicornUVLoopWebWorker',
    'GunicornWebWorker',
)


def __getattr__(name: str) -> object:  # noqa: WPS413 WPS433
    # ty aiohttp for this code <3
    global GunicornUVLoopWebWorker, GunicornWebWorker

    # Importing gunicorn takes a long time (>100ms), so only import if actually needed.
    if name in ('GunicornUVLoopWebWorker', 'GunicornWebWorker'):
        try:
            from aiohttp.worker import GunicornUVLoopWebWorker as guv, GunicornWebWorker as gw  # noqa: N813 WPS433
        except ImportError:
            return None

        GunicornUVLoopWebWorker = guv  # noqa: WPS442
        GunicornWebWorker = gw  # noqa: WPS442
        return guv if name == 'GunicornUVLoopWebWorker' else gw

    raise AttributeError(f'module {__name__} has no attribute {name}')
