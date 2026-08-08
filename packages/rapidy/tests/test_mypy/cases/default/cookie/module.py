from rapidy.parameters.http import Cookie, Cookies


def handler(
    _1: int = Cookie('1'),
    _2: int = Cookie(default_factory=lambda: '1'),
    _3: int = Cookie('1', default_factory=lambda: '1'),
    _4: int = Cookies('1'),
    _5: int = Cookies(default_factory=lambda: '1'),
    _6: int = Cookies('1', default_factory=lambda: '1'),
) -> None:
    pass
