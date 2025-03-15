from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from rapidy.encoders import jsonify

class InnerData(BaseModel):
    text: str = 'text'

class ComplexData(BaseModel):
    decimal: Decimal = Decimal('1.22223311')
    date: datetime = datetime.now()
    inner: InnerData = Field(default_factory=InnerData)

jsonify('text')  # 'text'
jsonify('text', dumps=True)  # '"text"'

jsonify(Decimal("1.22223311"))  # '1.22223311'

jsonify(ComplexData())  # {'decimal': '1.22223311', 'date': '2024-10-30T10:51:07.884276', 'inner': {'text': 'text'}}
jsonify(ComplexData(), dumps=True)  # '{"decimal": "1.22223311", "date": "2024-10-30T10:51:07.884276", "inner": {"text": "text"}}'