from rapidy.request_params import Cookie, CookieRaw, CookieSchema

Cookie('1')
Cookie(default_factory=lambda: '1')
Cookie('1', default_factory=lambda: '1')

CookieSchema('1')
CookieSchema(default_factory=lambda: '1')
CookieSchema('1', default_factory=lambda: '1')

CookieRaw('1')
CookieRaw(default_factory=lambda: '1')
CookieRaw('1', default_factory=lambda: '1')
