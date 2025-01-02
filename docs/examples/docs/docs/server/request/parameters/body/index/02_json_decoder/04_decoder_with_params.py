import json
from functools import partial
from typing import Any, OrderedDict
from rapidy.http import post, Body

decoder = partial(json.loads, object_pairs_hook=OrderedDict)

@post('/')
async def handler(
    data: Any = Body(json_decoder=decoder),
) -> ...: