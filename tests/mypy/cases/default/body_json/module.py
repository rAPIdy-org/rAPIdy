from rapidy.request_params import JsonBody, JsonBodyRaw, JsonBodySchema

JsonBody('1')
JsonBody(default_factory=lambda: '1')
JsonBody('1', default_factory=lambda: '1')

JsonBodySchema('1')
JsonBodySchema(default_factory=lambda: '1')
JsonBodySchema('1', default_factory=lambda: '1')

JsonBodyRaw('1')
JsonBodyRaw(default_factory=lambda: '1')
JsonBodyRaw('1', default_factory=lambda: '1')
