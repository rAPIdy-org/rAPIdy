from enum import Enum
from rapidy.http import post, Body, ContentType

class DataEnum(Enum):
    test = 'test'

@post('/')
async def handler(
    data: DataEnum | None = Body(content_type=ContentType.text_plain),
    # or
    data: Optional[DataEnum] = Body(content_type=ContentType.text_plain),
    # or
    data: Union[DataEnum, None] = Body(content_type=ContentType.text_plain),
) -> ...: