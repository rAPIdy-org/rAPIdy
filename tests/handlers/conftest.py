from typing import AsyncGenerator

import pytest
from aiohttp import FormData, MultipartWriter
from multidict import MultiDict

from rapidy.media_types import ApplicationBytes, ApplicationJSON, TextPlain


@pytest.fixture
def form_data_disptype_name() -> str:
    return "form-data"


def create_content_type_header(header: str) -> MultiDict[str]:
    return MultiDict({"content-type": header})


@pytest.fixture
def content_type_text_header() -> MultiDict[str]:
    return create_content_type_header(TextPlain)


@pytest.fixture
def content_type_json_header() -> MultiDict[str]:
    return create_content_type_header(ApplicationJSON)


@pytest.fixture
def content_type_app_binary_header() -> MultiDict[str]:
    return create_content_type_header(ApplicationBytes)


@pytest.fixture
async def multipart_writer(form_data_disptype_name: str) -> AsyncGenerator[MultipartWriter, None]:
    with MultipartWriter(form_data_disptype_name) as multipart_data:
        yield multipart_data


@pytest.fixture
async def x_www_form_writer(form_data_disptype_name: str) -> FormData:
    return FormData()
