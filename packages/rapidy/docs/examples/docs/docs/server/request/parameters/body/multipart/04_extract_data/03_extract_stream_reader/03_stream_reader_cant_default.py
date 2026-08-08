from rapidy import StreamReader
from rapidy.http import post, Body, ContentType

@post('/')
async def handler(
    user_data: StreamReader = Body(default='SomeDefault', content_type=ContentType.m_part_form_data),
) -> ...: