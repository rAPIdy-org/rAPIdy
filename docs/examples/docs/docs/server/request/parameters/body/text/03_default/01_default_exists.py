from enum import Enum
from rapidy.http import post, Body, ContentType

class DataEnum(Enum):
    test = 'test'

@post('/')
async def handler(
    data: DataEnum = Body('some_data', content_type=ContentType.text_plain),
    # or
    data: DataEnum = Body(default_factory=lambda: 'some_data', content_type=ContentType.text_plain),
) -> ...: