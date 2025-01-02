from pydantic import BaseModel, Field
from rapidy.encoders import jsonify

class Result(BaseModel):
    value: str = Field('data', alias='someValue')
    another_value: str = Field('another_data', alias='someAnotherValue')

jsonify(
    Result(someAnotherValue='new_data'),
    exclude_unset=False,  # <-- default
)
# {"someValue": "data", "someAnotherValue": "new_data"}

...

jsonify(
    Result(someAnotherValue='new_data'),
    exclude_unset=True,
)
# {"someAnotherValue": "new_data"}