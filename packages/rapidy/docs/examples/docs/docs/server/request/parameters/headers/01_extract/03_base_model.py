from pydantic import BaseModel, Field
from rapidy.http import get, Headers

class HeadersData(BaseModel):
    host: str = Field(alias='Host')
    keep_alive: str = Field(alias='Keep-Alive')

@get('/')
async def handler(
    headers_data: HeadersData = Headers(),
) -> ...: