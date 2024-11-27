from rapidy.parameters.http import Header, Headers


def handler(
        _1: int = Header('1'),
        _2: int = Header(default_factory=lambda: '1'),
        _3: int = Header('1', default_factory=lambda: '1'),
        _4: int = Headers('1'),
        _5: int = Headers(default_factory=lambda: '1'),
        _6: int = Headers('1', default_factory=lambda: '1'),
) -> None: pass
