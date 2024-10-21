from rapidy.request_parameters import Header, Headers

Header('1')
Header(default_factory=lambda: '1')
Header('1', default_factory=lambda: '1')

Headers('1')
Headers(default_factory=lambda: '1')
Headers('1', default_factory=lambda: '1')
