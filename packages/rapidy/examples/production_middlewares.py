from __future__ import annotations

from rapidy import Rapidy
from rapidy.http import get, Request
from rapidy.middlewares import (
    CompressionMiddleware,
    CORSMiddleware,
    HTTPSRedirectMiddleware,
    ProxyHeadersMiddleware,
    RequestIDMiddleware,
    TrustedHostMiddleware,
)


@get('/report')
async def report(request: Request) -> dict[str, str]:
    """Return enough data to observe request IDs and compression."""
    return {
        'request_id': request.state.request_id,
        'message': 'production middleware ' * 40,
    }


app = Rapidy(
    middlewares=[
        # The edge proxy must overwrite/sanitize forwarded fields before appending them.
        ProxyHeadersMiddleware(['127.0.0.1', '10.0.0.0/8']),
        TrustedHostMiddleware(['api.example.com', 'testserver']),
        HTTPSRedirectMiddleware(['api.example.com', 'testserver']),
        RequestIDMiddleware(),
        CORSMiddleware(
            allow_origins=['https://console.example.com'],
            allow_methods=['GET'],
            allow_headers=['authorization'],
            allow_credentials=True,
        ),
        CompressionMiddleware(algorithms=['br', 'gzip'], minimum_size=500),
    ],
    http_route_handlers=[report],
)
