from pydantic import BaseModel, Field
from rapidy.encoders import jsonify

class Result(BaseModel):
    value: str = Field('data', alias='someValue')

jsonify(
    Result(),
    response_exclude_defaults=True,
)
# {}