from rapidy.request_parameters import Body

Body('1')
Body(default_factory=lambda: '1')
Body('1', default_factory=lambda: '1')
