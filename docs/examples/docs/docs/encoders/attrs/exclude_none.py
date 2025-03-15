from pydantic import BaseModel, Field
from rapidy.encoders import jsonify

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    none_value: None = None

jsonify(
    Result(),
    exclude_none=True,
)
# {"someValue": "data"}

...

jsonify(
    Result(),
    exclude_none=False,  # default
)
# {"someValue": "data", "none_value": null}