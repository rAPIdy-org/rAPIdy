@middleware
async def hello_rapidy_middleware(
    request: Request,
    call_next: CallNext,
    response: Response,
) -> StreamResponse: