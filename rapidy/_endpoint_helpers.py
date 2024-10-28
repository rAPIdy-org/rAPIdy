from concurrent.futures import Executor
from typing import Optional, Union

from aiohttp.typedefs import JSONEncoder

from rapidy import web_response
from rapidy.encoders import CustomEncoder, Exclude, Include
from rapidy.enums import ContentType


def create_response(
        content_type: Union[str, ContentType, None],
        charset: str,
        zlib_executor: Optional[Executor],
        zlib_executor_size: Optional[int],
        # body preparer
        include: Optional[Include],
        exclude: Optional[Exclude],
        by_alias: bool,
        exclude_unset: bool,
        exclude_defaults: bool,
        exclude_none: bool,
        custom_encoder: Optional[CustomEncoder],
        json_encoder: JSONEncoder,
) -> web_response.Response:
    return web_response.Response(
        content_type=content_type,
        charset=charset,
        zlib_executor=zlib_executor,
        zlib_executor_size=zlib_executor_size,
        include=include,
        exclude=exclude,
        by_alias=by_alias,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
        custom_encoder=custom_encoder,
        json_encoder=json_encoder,
    )
