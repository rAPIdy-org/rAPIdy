from dataclasses import dataclass
from rapidy.http import get, QueryParams

@dataclass
class QueryParamsData:
    query: str
    star_rating: str

@get('/')
async def handler(
    query_params_data: QueryParamsData = QueryParams(),
) -> ...: