from __future__ import annotations

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from rapidy_core.enums import HTTPRequestParamType

from rapidy import Rapidy
from rapidy.http import Body, Cookie, Header, PathParam, post, QueryParam
from rapidy.routing.http.routers import get_route_parameters, HandlerParameterRecord


class Payload(BaseModel):
    value: int


def test_route_parameters_are_registration_time_public_metadata() -> None:
    async def handler(
        payload: Payload = Body(description='request body'),
        token: str = Header(alias='x-token'),
        item_id: int = PathParam(),
        page: int = QueryParam(alias='q'),
        session: str = Cookie(default='guest'),
    ) -> str:
        return 'ok'

    app = Rapidy(http_route_handlers=[post.reg('/items/{item_id}', handler)])
    route = next(record for record in app.routes if record.method == 'POST')
    parameters = get_route_parameters(route)

    assert parameters is route.parameters
    assert all(isinstance(parameter, HandlerParameterRecord) for parameter in parameters)
    assert all(isinstance(parameter.field_info, FieldInfo) for parameter in parameters)
    assert {parameter.param_type for parameter in parameters} == {
        HTTPRequestParamType.body,
        HTTPRequestParamType.header,
        HTTPRequestParamType.path,
        HTTPRequestParamType.query,
        HTTPRequestParamType.cookie,
    }
    by_name = {parameter.name: parameter for parameter in parameters}
    assert by_name['payload'].annotation is Payload
    assert by_name['payload'].field_info.description == 'request body'
    assert by_name['token'].alias == 'x-token'
    assert by_name['page'].alias == 'q'
    assert by_name['session'].required is False
    assert by_name['session'].default == 'guest'
    assert all(parameter.source is parameter.param_type for parameter in parameters)
