from rapidy.request_parameters import QueryParam, QueryParams

QueryParam('1')
QueryParam(default_factory=lambda: '1')
QueryParam('1', default_factory=lambda: '1')

QueryParams('1')
QueryParams(default_factory=lambda: '1')
QueryParams('1', default_factory=lambda: '1')
