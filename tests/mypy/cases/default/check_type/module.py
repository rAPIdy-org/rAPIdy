from rapidy.request_params import Header, HeaderRaw, HeaderSchema
from rapidy.web import View


def handler(
        param_1: int = Header(1),
        param_2: int = Header('1'),
        param_3: int = Header(default_factory=lambda: '1'),
        param_4: int = HeaderSchema(1),
        param_5: int = HeaderSchema('1'),
        param_6: int = HeaderSchema(default_factory=lambda: '1'),
        param_7: int = HeaderRaw(1),
        param_8: int = HeaderRaw('1'),
        param_9: int = HeaderRaw(default_factory=lambda: '1'),
) -> None: pass


class Handler(View):
    def post(
            self,
            param_1: int = Header(1),
            param_2: int = Header('1'),
            param_3: int = Header(default_factory=lambda: '1'),
            param_4: int = HeaderSchema(1),
            param_5: int = HeaderSchema('1'),
            param_6: int = HeaderSchema(default_factory=lambda: '1'),
            param_7: int = HeaderRaw(1),
            param_8: int = HeaderRaw('1'),
            param_9: int = HeaderRaw(default_factory=lambda: '1'),
    ): pass
