from rapidy_core.parameters.http import Header, Headers  # noqa: I001
from rapidy.typedefs import View


def handler(  # noqa: PLR0917
    param_1: int = Header(1),
    param_2: int = Header('1'),
    param_3: int = Header(default_factory=lambda: '1'),
    param_4: int = Headers(1),
    param_5: int = Headers('1'),
    param_6: int = Headers(default_factory=lambda: '1'),
) -> None:
    pass


class Handler(View):
    def post(  # noqa: PLR0917
        self,
        param_1: int = Header(1),
        param_2: int = Header('1'),
        param_3: int = Header(default_factory=lambda: '1'),
        param_4: int = Headers(1),
        param_5: int = Headers('1'),
        param_6: int = Headers(default_factory=lambda: '1'),
    ) -> None:
        pass
