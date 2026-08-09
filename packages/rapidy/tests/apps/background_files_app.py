from pathlib import Path

from rapidy import Rapidy
from rapidy.http import get
from rapidy.responses import FileResponse
from rapidy.staticfiles import StaticFiles

ASSET_DIR = Path(__file__).with_name('static_assets')


@get('/download')
async def download() -> FileResponse:
    return FileResponse(ASSET_DIR / 'range.txt')


app = Rapidy(
    http_route_handlers=[
        download,
        StaticFiles('/static', directory=ASSET_DIR, html=True),
    ]
)
