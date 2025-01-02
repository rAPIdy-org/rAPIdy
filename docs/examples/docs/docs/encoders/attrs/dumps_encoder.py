from typing import Any
from rapidy.encoders import jsonify

def custom_encoder(obj: Any) -> str:
    ...

jsonify(
    'data',
    dumps_encoder=custom_encoder,
)