from concurrent.futures import Executor
from typing import Optional, Union

from rapidy import web_response
from rapidy.enums import ContentType


def create_response(
        content_type: Union[str, ContentType],
        charset: str,
        zlib_executor: Optional[Executor],
        zlib_executor_size: Optional[int],
) -> web_response.Response:
    return web_response.Response(
        content_type=content_type,
        charset=charset,
        zlib_executor=zlib_executor,
        zlib_executor_size=zlib_executor_size,
    )
