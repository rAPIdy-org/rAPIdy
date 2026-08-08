from rapidy.http import get
from rapidy.parameters.http import PathParam, Header, Cookie, QueryParam, Body

@get('/{user_id}')
async def handler(
        user_id: int = PathParam(),
        host: str = Header(alias='Host'),
        session: str = Cookie(alias='UserSession'),
        age_filter: str = QueryParam(alias='AgeFilter'),
        data: str = Body(),
) -> ...: