from rapidy.parameters.http import PathParam, PathParams


def handler(
    _1: int = PathParam('1'),
    _2: int = PathParam(default_factory=lambda: '1'),
    _3: int = PathParam('1', default_factory=lambda: '1'),
    _4: int = PathParams('1'),
    _5: int = PathParams(default_factory=lambda: '1'),
    _6: int = PathParams('1', default_factory=lambda: '1'),
) -> None:
    pass
