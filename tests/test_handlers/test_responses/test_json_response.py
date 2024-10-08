from typing import Dict, Final

from aiohttp.pytest_plugin import AiohttpClient
from pydantic import BaseModel, ConfigDict, Field

from rapidy import web
from rapidy._constants import PYDANTIC_V1, PYDANTIC_V2

PATH: Final[str] = '/'


class Response(BaseModel):
    test: str = Field(alias='Test')

    if PYDANTIC_V1:
        class Config:
            allow_population_by_field_name = True,

    elif PYDANTIC_V2:
        model_config: ConfigDict = ConfigDict(populate_by_name=True)

    else:
        raise ValueError


async def test_json_response_base_model(aiohttp_client: AiohttpClient) -> None:
    expected_data: Dict[str, str] = {
        'Test': 'test',
    }

    async def handler() -> web.Response:
        return web.json_response(Response(test='test'))

    app = web.Application()
    app.add_routes([web.get(PATH, handler)])

    client = await aiohttp_client(app)
    resp = await client.get(PATH)

    json_data = await resp.json()
    assert json_data == expected_data


async def test_json_response_str(aiohttp_client: AiohttpClient) -> None:
    expected_data: str = 'test'

    async def handler() -> web.Response:
        return web.json_response(expected_data)

    app = web.Application()
    app.add_routes([web.get(PATH, handler)])

    client = await aiohttp_client(app)
    resp = await client.get(PATH)

    json_data = await resp.json()
    assert json_data == expected_data
