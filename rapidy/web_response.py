from typing import Any, Optional, Union

from aiohttp.typedefs import JSONEncoder, LooseHeaders
from aiohttp.web_response import ContentCoding, Response, StreamResponse

from rapidy._base_exceptions import RapidyException
from rapidy._constants import DEFAULT_DUMPS_ENCODER
from rapidy.encoders import CustomEncoder, Exclude, Include, simplify_data
from rapidy.enums import Charset, ContentType

__all__ = (
    'ContentCoding',
    'StreamResponse',
    'Response',
    'json_response',
    'JsonResponse',
)


class ResponseDataNotStrError(RapidyException):
    message = 'Json response data is not str. Use (dumps=True, ...) attribute to convert obj to str.'


def json_response(
        obj: Optional[Any] = None,
        *,
        # Response attrs
        status: int = 200,
        headers: Optional[LooseHeaders] = None,
        # encoder attrs
        include: Optional[Include] = None,
        exclude: Optional[Exclude] = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        custom_encoder: Optional[CustomEncoder] = None,
        charset: Union[str, Charset] = Charset.utf8,
        dumps: bool = True,
        dumps_encoder: JSONEncoder = DEFAULT_DUMPS_ENCODER,
) -> Response:
    """Low-level factory. Required to explicitly create a json response.

    Note:
        This factory is not needed in most scenarios.

    Args:
        obj:
            The input object something that can be encoded in JSON.
        status:
            The status code of the response.
        headers:
            The headers of the response.
        include:
            Pydantic's `include` parameter, passed to Pydantic models to set the fields to include.
        exclude:
            Pydantic's `exclude` parameter, passed to Pydantic models to set the fields to exclude.
        by_alias:
            Pydantic's `by_alias` parameter, passed to Pydantic models to define
            if the output should use the alias names (when provided) or the Python
            attribute names. In an API, if you set an alias, it's probably because you
            want to use it in the result, so you probably want to leave this set to `True`.
        exclude_unset:
            Pydantic's `exclude_unset` parameter, passed to Pydantic models to define
            if it should exclude from the output the fields that were not explicitly
            set (and that only had their default values).
        exclude_defaults:
            Pydantic's `exclude_defaults` parameter, passed to Pydantic models to define
            if it should exclude from the output the fields that had the same default
            value, even when they were explicitly set.
        exclude_none:
            Pydantic's `exclude_none` parameter, passed to Pydantic models to define
            if it should exclude from the output any fields that have a `None` value.
        custom_encoder:
            Pydantic's `custom_encoder` parameter, passed to Pydantic models to define a custom encoder.
        charset:
            The `charset` that will be used to encode and decode obj data.
        dumps:
            Arg that determines whether to make a string from the created object.
        dumps_encoder:
            Any callable that accepts an object and returns a JSON string.
            Will be used if prepare_to_json(dumps=True, ...).
    """
    if obj is not None:
        obj = simplify_data(
            obj,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            custom_encoder=custom_encoder,
            charset=charset,
            dumps=dumps,
            dumps_encoder=dumps_encoder,
        )

    if not isinstance(obj, str):
        raise ResponseDataNotStrError

    return Response(
        text=obj,
        status=status,
        headers=headers,
        content_type=ContentType.json,
    )


JsonResponse = json_response
