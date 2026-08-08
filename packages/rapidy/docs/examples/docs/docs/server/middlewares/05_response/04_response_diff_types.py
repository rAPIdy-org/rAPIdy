@middleware
async def my_middleware(
    request: Request,
    call_next: CallNext,
) -> int | str | StreamResponse:  # or Union[int, str, StreamResponse]
    if ...:
        return 1
    elif ...:
        return 'string'
    return await call_next(request)