from rapidy.parameters.http import Body


def handler(
        _1: int = Body('1'),
        _2: int = Body(default_factory=lambda: '1'),
        _3: int = Body('1', default_factory=lambda: '1'),
) -> None: pass
