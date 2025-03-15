from pydantic import BaseModel, Field
from rapidy.encoders import jsonify

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    another_value: str = Field('another_data', alias='someAnotherValue')

jsonify(
    Result(),
    include={'value'},
)
# {'someValue': 'data'}