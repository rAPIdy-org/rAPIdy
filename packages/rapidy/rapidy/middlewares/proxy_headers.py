from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from ipaddress import ip_address, ip_network, IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Literal, TYPE_CHECKING
from urllib.parse import urlsplit

from ._utils import replace_request_header, split_quoted, unquote_header_value

if TYPE_CHECKING:
    from rapidy.request import Request
    from rapidy.typedefs import CallNext, HTTPResponse

__all__ = ('ProxyHeaderMode', 'ProxyHeadersMiddleware')

_MAX_PORT = 65535

type IPAddress = IPv4Address | IPv6Address
type IPNetwork = IPv4Network | IPv6Network
type ProxyHeaderMode = Literal['forwarded', 'x-forwarded', 'both']


@dataclass(frozen=True, slots=True)
class _ForwardedElement:
    node: tuple[IPAddress, int | None] | None
    proto: str | None
    host: str | None


class ProxyHeadersMiddleware:
    """Honor forwarding headers only across explicitly trusted proxy networks."""

    __slots__ = ('_header_mode', '_trusted_proxies')

    def __init__(
        self,
        trusted_proxies: Iterable[str],
        *,
        headers: ProxyHeaderMode = 'both',
    ) -> None:
        networks = tuple(ip_network(value, strict=False) for value in trusted_proxies)
        if not networks:
            msg = 'trusted_proxies must contain at least one IP address or CIDR network'
            raise ValueError(msg)
        if headers not in ('forwarded', 'x-forwarded', 'both'):
            msg = "headers must be 'forwarded', 'x-forwarded', or 'both'"
            raise ValueError(msg)
        self._trusted_proxies: tuple[IPNetwork, ...] = networks
        self._header_mode = headers

    async def __call__(self, request: Request, call_next: CallNext) -> HTTPResponse:
        """Normalize trusted connection metadata before downstream dispatch."""
        if not self._peer_is_trusted(request):
            return await call_next(request)

        forwarded_values = request.headers.getall('forwarded', [])
        used_forwarded = False
        if self._header_mode in ('forwarded', 'both') and forwarded_values:
            used_forwarded = self._apply_forwarded(request, ','.join(forwarded_values))
        if self._header_mode in ('x-forwarded', 'both') and not forwarded_values and not used_forwarded:
            self._apply_x_forwarded(request)
        return await call_next(request)

    def _peer_is_trusted(self, request: Request) -> bool:
        client = request.scope.get('client')
        if not isinstance(client, (tuple, list)) or not client:
            return False
        try:
            peer = ip_address(str(client[0]))
        except ValueError:
            return False
        return self._is_trusted(peer)

    def _is_trusted(self, address: IPAddress) -> bool:
        return any(address in network for network in self._trusted_proxies if address.version == network.version)

    def _apply_forwarded(self, request: Request, value: str) -> bool:
        elements = _parse_forwarded(value)
        selected = self._select_forwarded(elements)
        if selected is None:
            return False
        self._apply_connection_metadata(
            request,
            node=selected.node,
            proto=selected.proto,
            host=selected.host,
        )
        return True

    def _select_forwarded(self, elements: Sequence[_ForwardedElement]) -> _ForwardedElement | None:
        selected: _ForwardedElement | None = None
        for element in reversed(elements):
            if element.node is None:
                return None
            selected = element
            if not self._is_trusted(element.node[0]):
                break
        return selected

    def _apply_x_forwarded(self, request: Request) -> None:
        forwarded_for = ','.join(request.headers.getall('x-forwarded-for', []))
        nodes = [_parse_node(item.strip()) for item in forwarded_for.split(',') if item.strip()]
        if any(node is None for node in nodes):
            return
        selected: tuple[IPAddress, int | None] | None = None
        for node in reversed(nodes):
            if node is None:
                return
            selected = node
            if not self._is_trusted(node[0]):
                break
        proto = _first_csv_value(request.headers.get('x-forwarded-proto'))
        host = _first_csv_value(request.headers.get('x-forwarded-host'))
        self._apply_connection_metadata(request, node=selected, proto=proto, host=host)

    @staticmethod
    def _apply_connection_metadata(
        request: Request,
        *,
        node: tuple[IPAddress, int | None] | None,
        proto: str | None,
        host: str | None,
    ) -> None:
        if node is not None:
            request.scope['client'] = (str(node[0]), node[1] if node[1] is not None else 0)
        normalized_proto = proto.lower() if proto is not None else None
        if normalized_proto in ('http', 'https'):
            request.scope['scheme'] = normalized_proto
        authority = _parse_authority(host) if host is not None else None
        if authority is not None:
            hostname, port, serialized = authority
            replace_request_header(request, 'host', serialized)
            default_port = 443 if request.scope.get('scheme') == 'https' else 80
            request.scope['server'] = (hostname, port if port is not None else default_port)


def _parse_forwarded(value: str) -> tuple[_ForwardedElement, ...]:
    result: list[_ForwardedElement] = []
    for raw_element in split_quoted(value, ','):
        parameters: dict[str, str] = {}
        valid = True
        for raw_parameter in split_quoted(raw_element, ';'):
            name, separator, raw_value = raw_parameter.partition('=')
            normalized_name = name.strip().lower()
            if not separator or not normalized_name or normalized_name in parameters:
                valid = False
                break
            parameters[normalized_name] = unquote_header_value(raw_value.strip())
        if not valid or 'for' not in parameters:
            return ()
        proto = parameters.get('proto')
        if proto is not None and proto.lower() not in ('http', 'https'):
            proto = None
        host = parameters.get('host')
        if host is not None and _parse_authority(host) is None:
            host = None
        result.append(_ForwardedElement(node=_parse_node(parameters['for']), proto=proto, host=host))
    return tuple(result)


def _parse_node(value: str) -> tuple[IPAddress, int | None] | None:
    if not value or value.lower() == 'unknown' or value.startswith('_'):
        return None
    host = value
    port: int | None = None
    if value.startswith('['):
        closing = value.find(']')
        if closing < 0:
            return None
        host = value[1:closing]
        suffix = value[closing + 1 :]
        if suffix:
            if not suffix.startswith(':') or not suffix[1:].isdigit():
                return None
            port = int(suffix[1:])
    elif value.count(':') == 1:
        candidate_host, candidate_port = value.rsplit(':', 1)
        if candidate_port.isdigit():
            host = candidate_host
            port = int(candidate_port)
    try:
        address = ip_address(host)
    except ValueError:
        return None
    if port is not None and not 0 <= port <= _MAX_PORT:
        return None
    return address, port


def _parse_authority(value: str) -> tuple[str, int | None, str] | None:
    if not value or any(character in value for character in '/?#@'):
        return None
    try:
        parsed = urlsplit(f'//{value}')
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None
    if host is None:
        return None
    serialized_host = f'[{host}]' if ':' in host else host
    serialized = f'{serialized_host}:{port}' if port is not None else serialized_host
    return host, port, serialized


def _first_csv_value(value: str | None) -> str | None:
    if value is None:
        return None
    first = value.partition(',')[0].strip()
    return first or None
