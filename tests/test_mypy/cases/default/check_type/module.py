from rapidy.parameters.http import Header, Headers
from rapidy.web import View


def handler(
    param_1: int = Header(1),
    param_2: int = Header('1'),
    param_3: int = Header(default_factory=lambda: '1'),
    param_4: int = Headers(1),
    param_5: int = Headers('1'),
    param_6: int = Headers(default_factory=lambda: '1'),
) -> None:
    pass


class Handler(View):
    def post(
        self,
        param_1: int = Header(1),
        param_2: int = Header('1'),
        param_3: int = Header(default_factory=lambda: '1'),
        param_4: int = Headers(1),
        param_5: int = Headers('1'),
        param_6: int = Headers(default_factory=lambda: '1'),
    ) -> None:
        pass
