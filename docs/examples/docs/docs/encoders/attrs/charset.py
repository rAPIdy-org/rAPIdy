from rapidy.enums import Charset
from rapidy.encoders import jsonify

jsonify(
    'data',
    charset=Charset.utf32,
    # or
    charset='utf32',
)
