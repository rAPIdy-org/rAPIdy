from __future__ import annotations

from pathlib import Path

from rapidy import Rapidy
from rapidy.background import BackgroundTasks
from rapidy.http import get, post, Response
from rapidy.responses import FileResponse
from rapidy.staticfiles import StaticFiles

ASSET_DIR = Path(__file__).with_name('assets')
notifications: list[str] = []


async def notify_export_ready(export_id: int) -> None:
    """Record a small post-response notification for the example."""
    notifications.append(f'export:{export_id}')


@post('/exports')
async def create_export() -> Response:
    """Accept an export and notify after the response is sent."""
    tasks = BackgroundTasks()
    tasks.add_task(notify_export_ready, 20)
    return Response({'accepted': True}, status=202, background=tasks)


@get('/downloads/report')
async def download_report() -> FileResponse:
    """Serve a range-aware attachment."""
    return FileResponse(ASSET_DIR / 'report.txt', filename='report.txt')


app = Rapidy(
    http_route_handlers=[
        create_export,
        download_report,
        StaticFiles('/assets', directory=ASSET_DIR, html=True, public=True),
    ]
)
