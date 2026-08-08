from rapidy.encoders import jsonify

jsonify('text')  # 'text'
jsonify('text', dumps=True)  # '"text"'