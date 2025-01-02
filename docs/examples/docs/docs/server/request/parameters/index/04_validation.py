@get('/')
async def handler(
    positive: int = QueryParam(gt=0),
    non_negative: int = QueryParam(ge=0),
    negative: int = QueryParam(lt=0),
    non_positive: int = QueryParam(le=0),
    even: int = QueryParam(multiple_of=2),
    love_for_pydantic: float = QueryParam(allow_inf_nan=True),
    short: str = QueryParam(min_length=3),
    long: str = QueryParam(max_length=10),
    regex: str = QueryParam(pattern=r'^\d*$'),
    precise: Decimal = QueryParam(max_digits=5, decimal_places=2),
) -> ...:
    ...