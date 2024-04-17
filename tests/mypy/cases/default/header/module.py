from rapidy.request_params import Header, HeaderRaw, HeaderSchema

Header('1')
Header(default_factory=lambda: '1')
Header('1', default_factory=lambda: '1')

HeaderSchema('1')
HeaderSchema(default_factory=lambda: '1')
HeaderSchema('1', default_factory=lambda: '1')

HeaderRaw('1')
HeaderRaw(default_factory=lambda: '1')
HeaderRaw('1', default_factory=lambda: '1')
