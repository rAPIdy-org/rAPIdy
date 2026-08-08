from pydantic import BaseModel, ConfigDict
from rapidy.http import post, Body, ContentType, FileField

class UserData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    username: str
    password: str
    image: FileField

@post('/')
async def handler(
    user_data: UserData = Body(content_type=ContentType.m_part_form_data),
    # or
    user_data: UserData = Body(content_type='multipart/form-data'),
) -> ...: