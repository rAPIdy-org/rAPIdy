import errno
import socket
import ssl

import httpcore2
import httpx2
from rapidy_client.errors import (
    ConnectError,
    DecodeError,
    DNSResolveError,
    HttpClientError,
    HttpTimeoutError,
    ProtocolError,
    ProxyError,
    ServerDisconnectedError,
    TLSError,
    TransportError,
)
from rapidy_client.transports.httpx import map_transport_exception


def _caused_by(error: BaseException, cause: BaseException) -> BaseException:
    error.__cause__ = cause
    return error


def test_connect_error_with_gaierror_maps_dns() -> None:
    source = _caused_by(
        httpx2.ConnectError("dns failed"),
        socket.gaierror(socket.EAI_NONAME, "not found"),
    )
    assert isinstance(map_transport_exception(source), DNSResolveError)


def test_connect_error_with_ssl_cert_maps_tls() -> None:
    source = _caused_by(
        httpx2.ConnectError("tls failed"),
        ssl.SSLCertVerificationError(1, "bad certificate"),
    )
    assert isinstance(map_transport_exception(source), TLSError)


def test_connect_error_with_ssl_error_maps_tls() -> None:
    source = _caused_by(httpx2.ConnectError("tls failed"), ssl.SSLError("bad"))
    assert isinstance(map_transport_exception(source), TLSError)


def test_proxy_error_maps_proxy() -> None:
    result = map_transport_exception(httpx2.ProxyError("proxy failed"))
    assert isinstance(result, ProxyError)
    assert not isinstance(result, ConnectError)


def test_connect_error_plain_maps_connect() -> None:
    assert type(map_transport_exception(httpx2.ConnectError("failed"))) is ConnectError


def test_remote_protocol_disconnect_maps_server_disconnected() -> None:
    message = "Server disconnected without sending a response."
    source = _caused_by(
        httpx2.RemoteProtocolError(message),
        httpcore2.RemoteProtocolError(message),
    )
    assert isinstance(map_transport_exception(source), ServerDisconnectedError)


def test_read_error_maps_transport_preserves_errno() -> None:
    os_error = OSError(errno.ECONNRESET, "reset")
    source = _caused_by(httpx2.ReadError("read failed"), os_error)
    result = map_transport_exception(source)
    assert type(result) is TransportError
    assert result.__cause__ is source
    assert source.__cause__ is os_error
    assert os_error.errno == errno.ECONNRESET


def test_write_error_maps_transport() -> None:
    assert type(map_transport_exception(httpx2.WriteError("failed"))) is TransportError


def test_remote_protocol_other_maps_protocol() -> None:
    result = map_transport_exception(httpx2.RemoteProtocolError("malformed headers"))
    assert isinstance(result, ProtocolError)
    assert not isinstance(result, ServerDisconnectedError)


def test_connect_timeout_maps_connect_phase() -> None:
    result = map_transport_exception(httpx2.ConnectTimeout("timeout"))
    assert isinstance(result, HttpTimeoutError)
    assert result.phase == "connect"


def test_read_timeout_maps_read_phase() -> None:
    result = map_transport_exception(httpx2.ReadTimeout("timeout"))
    assert isinstance(result, HttpTimeoutError)
    assert result.phase == "read"


def test_pool_timeout_maps_pool_phase() -> None:
    result = map_transport_exception(httpx2.PoolTimeout("timeout"))
    assert isinstance(result, HttpTimeoutError)
    assert result.phase == "pool"


def test_write_timeout_maps_write_phase() -> None:
    result = map_transport_exception(httpx2.WriteTimeout("timeout"))
    assert isinstance(result, HttpTimeoutError)
    assert result.phase == "write"


def test_asyncio_timeout_maps_total_phase() -> None:
    result = map_transport_exception(TimeoutError("timeout"))
    assert isinstance(result, HttpTimeoutError)
    assert result.phase == "total"


def test_invalid_url_maps_valueerror() -> None:
    result = map_transport_exception(httpx2.InvalidURL("bad url"))
    assert isinstance(result, ValueError)
    assert not isinstance(result, HttpClientError)


def test_unsupported_protocol_maps_valueerror() -> None:
    assert isinstance(
        map_transport_exception(httpx2.UnsupportedProtocol("bad scheme")),
        ValueError,
    )


def test_decoding_error_maps_decode() -> None:
    assert isinstance(
        map_transport_exception(httpx2.DecodingError("bad encoding")),
        DecodeError,
    )


def test_unknown_httpx_transport_error_maps_catchall() -> None:
    source = httpx2.TransportError("unknown")
    result = map_transport_exception(source)
    assert type(result) is TransportError
    assert result.__cause__ is source


def test_unknown_non_httpx_maps_catchall() -> None:
    source = RuntimeError("boom")
    result = map_transport_exception(source)
    assert type(result) is TransportError
    assert result.__cause__ is source


def test_cause_chain_prefers_specific_over_generic() -> None:
    ssl_error = ssl.SSLError("tls")
    generic = _caused_by(OSError("generic"), ssl_error)
    source = _caused_by(httpx2.ConnectError("connect"), generic)
    assert isinstance(map_transport_exception(source), TLSError)
