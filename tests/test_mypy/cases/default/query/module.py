from rapidy.parameters.http import QueryParam, QueryParams


def handler(
        _1: int = QueryParam('1'),
        _2: int = QueryParam(default_factory=lambda: '1'),
        _3: int = QueryParam('1', default_factory=lambda: '1'),
        _4: int = QueryParams('1'),
        _5: int = QueryParams(default_factory=lambda: '1'),
        _6: int = QueryParams('1', default_factory=lambda: '1'),
) -> None: pass
