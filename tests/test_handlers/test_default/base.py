from dataclasses import dataclass, field
from typing import Any, Dict, Type

from aiohttp import MultipartWriter, StreamReader

from rapidy.enums import ContentType
from rapidy.request_parameters import Body, Cookie, Cookies, Header, PathParam, PathParams, QueryParam, QueryParams, \
    ParamFieldInfo
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
    content_type: ContentType = ContentType.json


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
        content_type=ContentType.json,
        request_kwargs={'json': {}},
    ),
    BodyTestCase(
        id='x-www-form-urlencoded',
        content_type=ContentType.x_www_form,
        request_kwargs={'data': ' '},
    ),
    BodyTestCase(
        id='multipart-body',
        content_type=ContentType.m_part_form_data,
        request_kwargs={'data': multipart_writer},
    ),
    BodyTestCase(
        id='text-body',
        content_type=ContentType.text_plain,
        request_kwargs={'data': ' '},
    ),
    BodyTestCase(
        id='bytes-body',
        content_type=ContentType.stream,
        request_kwargs={'data': ' '},
    ),
    BodyTestCase(
        id='stream-body',
        content_type=ContentType.stream,
        annotation=StreamReader,
        request_kwargs={'data': ' '},
    ),
)
