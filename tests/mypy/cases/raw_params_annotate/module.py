from typing import Any, Dict, List, Union

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
        form_data_1: Dict[str, int] = FormDataBodyRaw(),
        form_data_2: Dict[str, str] = FormDataBodyRaw(duplicated_attrs_parse_as_array=True),
        form_data_3: Dict[str, List[str]] = FormDataBodyRaw(duplicated_attrs_parse_as_array=True),
        multipart_1: Dict[str, Any] = MultipartBodyRaw(),
        multipart_3: Dict[int, Any] = MultipartBodyRaw(duplicated_attrs_parse_as_array=True),
        multipart_4: Dict[str, List[Any]] = MultipartBodyRaw(duplicated_attrs_parse_as_array=True),
) -> None: pass


class Handler(View):
    def post(
            self,
            path: int = PathRaw(),
            headers: int = HeaderRaw(),
            cookies: int = CookieRaw(),
            query: int = QueryRaw(),
            json: Dict[str, Any] = JsonBodyRaw(),
            form_data_1: Dict[str, int] = FormDataBodyRaw(),
            form_data_2: Dict[str, str] = FormDataBodyRaw(duplicated_attrs_parse_as_array=True),
            form_data_3: Dict[str, List[str]] = FormDataBodyRaw(duplicated_attrs_parse_as_array=True),
            multipart_1: Dict[str, Any] = MultipartBodyRaw(),
            multipart_3: Dict[int, Any] = MultipartBodyRaw(duplicated_attrs_parse_as_array=True),
            multipart_4: Dict[str, List[Any]] = MultipartBodyRaw(duplicated_attrs_parse_as_array=True),
    ): pass
