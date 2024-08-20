from rapidy.request_parameters import PathParam, PathParams

PathParam('1')
PathParam(default_factory=lambda: '1')
PathParam('1', default_factory=lambda: '1')

PathParams('1')
PathParams(default_factory=lambda: '1')
PathParams('1', default_factory=lambda: '1')
