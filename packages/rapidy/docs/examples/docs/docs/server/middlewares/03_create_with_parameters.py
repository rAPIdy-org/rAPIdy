@middleware(
    response_validate=...,
    response_type = ...,
    response_content_type = ...,
    response_charset = ...,
    response_zlib_executor = ...,
    response_zlib_executor_size = ...,
    response_include_fields = ...,
    response_exclude_fields = ...,
    response_by_alias = ...,
    response_exclude_unset = ...,
    response_exclude_defaults = ...,
    response_exclude_none = ...,
    response_custom_encoder = ...,
    response_json_encoder = ...,
)
async def hello_middleware(request: Request, call_next: CallNext) -> StreamResponse: