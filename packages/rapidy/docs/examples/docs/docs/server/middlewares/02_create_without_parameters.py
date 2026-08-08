@middleware
async def hello_middleware(request: Request, call_next: CallNext) -> StreamResponse: