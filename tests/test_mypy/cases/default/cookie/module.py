from rapidy.request_parameters import Cookie, Cookies

Cookie('1')
Cookie(default_factory=lambda: '1')
Cookie('1', default_factory=lambda: '1')

Cookies('1')
Cookies(default_factory=lambda: '1')
Cookies('1', default_factory=lambda: '1')
