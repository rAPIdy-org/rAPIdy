from rapidy.request_params import Query, QueryRaw, QuerySchema

Query('1')
Query(default_factory=lambda: '1')
Query('1', default_factory=lambda: '1')

QuerySchema('1')
QuerySchema(default_factory=lambda: '1')
QuerySchema('1', default_factory=lambda: '1')

QueryRaw('1')
QueryRaw(default_factory=lambda: '1')
QueryRaw('1', default_factory=lambda: '1')
