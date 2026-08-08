from pydantic import BaseModel, Field
from rapidy.encoders import jsonify

class Result(BaseModel):
    value: str = Field('data', alias='someValue')

jsonify(
    Result(),
    by_alias=True,  # <-- default
)
# {"someValue": "data"}

...

jsonify(
    Result(),
    by_alias=False,
)
# {"value": "data"}