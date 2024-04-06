from typing import Any, Dict

from rapidy.request_params import (
    CookieRaw,
    FormDataBodyRaw,
    HeaderRaw,
    JsonBodyRaw,
    MultipartBodyRaw,
    PathRaw,
    QueryRaw,
)
from rapidy.web import View


def handler(
        path: int = PathRaw(),
        headers: int = HeaderRaw(),
        cookies: int = CookieRaw(),
        query: int = QueryRaw(),
        json: Dict[str, Any] = JsonBodyRaw(),
        form_data: Dict[str, Any] = FormDataBodyRaw(),
        multipart: Dict[str, Any] = MultipartBodyRaw(),
) -> None: pass


class Handler(View):
    def post(
            self,
            path: int = PathRaw(),
            headers: int = HeaderRaw(),
            cookies: int = CookieRaw(),
            query: int = QueryRaw(),
            json: Dict[str, Any] = JsonBodyRaw(),
            form_data: Dict[str, Any] = FormDataBodyRaw(),
            multipart: Dict[str, Any] = MultipartBodyRaw(),
    ): pass
