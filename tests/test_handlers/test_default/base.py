from dataclasses import dataclass, field
from typing import Any, Dict, Type

from aiohttp import MultipartWriter, StreamReader

from rapidy._request_param_field_info import ParamFieldInfo
from rapidy.request_enums import BodyType
from rapidy.request_parameters import Body, Cookie, Cookies, Header, PathParam, PathParams, QueryParam, QueryParams
from tests.helpers import BOUNDARY

multipart_writer = MultipartWriter(boundary=BOUNDARY)


@dataclass
class TestCase:
    id: str
    param_type: Type[ParamFieldInfo]
    annotation: Any = Any
    request_kwargs: Dict[str, Any] = field(default_factory=dict)

    __test__ = False


@dataclass
class BodyTestCase(TestCase):
    param_type: Type[Body] = Body
    body_type: BodyType = BodyType.json


params_test_cases = (
    TestCase(
        id='path-param',
        param_type=PathParam,
    ),
    TestCase(
        id='path-params',
        param_type=PathParams,
    ),
    TestCase(
        id='header',
        param_type=Header,
    ),
    # NOTE: not check `Headers` as it always contains data
    TestCase(
        id='cookie',
        param_type=Cookie,
    ),
    TestCase(
        id='cookies',
        param_type=Cookies,
    ),
    TestCase(
        id='query-param',
        param_type=QueryParam,
    ),
    TestCase(
        id='query-params',
        param_type=QueryParams,
    ),
)

body_test_cases = (
    BodyTestCase(
        id='json',
        body_type=BodyType.json,
        request_kwargs={'json': {}},
    ),
    BodyTestCase(
        id='x-www-form-urlencoded',
        body_type=BodyType.x_www_form,
        request_kwargs={'data': ' '},
    ),
    BodyTestCase(
        id='multipart-body',
        body_type=BodyType.multipart_form_data,
        request_kwargs={'data': multipart_writer},
    ),
    BodyTestCase(
        id='text-body',
        body_type=BodyType.text,
        request_kwargs={'data': ' '},
    ),
    BodyTestCase(
        id='bytes-body',
        body_type=BodyType.binary,
        request_kwargs={'data': ' '},
    ),
    BodyTestCase(
        id='stream-body',
        body_type=BodyType.binary,
        annotation=StreamReader,
        request_kwargs={'data': ' '},
    ),
)
