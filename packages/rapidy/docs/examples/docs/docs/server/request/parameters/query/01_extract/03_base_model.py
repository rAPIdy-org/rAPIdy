from pydantic import BaseModel
from rapidy.http import get, QueryParams

class QueryParamsData(BaseModel):
    query: str
    star_rating: str

@get('/')
async def handler(
    query_params_data: QueryParamsData = QueryParams(),
) -> ...: