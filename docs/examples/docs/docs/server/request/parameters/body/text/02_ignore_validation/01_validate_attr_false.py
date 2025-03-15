from enum import Enum
from rapidy.http import post, Body, ContentType

class DataEnum(Enum):
    test = 'test'

@post('/')
async def handler(
    data: DataEnum = Body(validate=False, content_type=ContentType.text_plain),
) -> ...: