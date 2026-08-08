from pydantic import BaseModel


class UserIn(BaseModel):
    id: int
    name: str
    email: str
    tags: list[str]


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    tags: list[str]
    processed: bool = True
