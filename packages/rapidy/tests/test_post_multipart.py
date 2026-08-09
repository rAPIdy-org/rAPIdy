from __future__ import annotations

from dataclasses import replace
from typing import Any, cast
from urllib.parse import quote

import pytest
from multidict import CIMultiDictProxy, MultiDictProxy

from rapidy import Rapidy
from rapidy.exceptions import HTTPRequestEntityTooLarge
from rapidy.request import FileField, MultipartLimits
from tests.request_factory import make_request


def multipart_body(boundary: str, parts: list[tuple[list[bytes], bytes]]) -> bytes:
    output = bytearray()
    for headers, body in parts:
        output.extend(f'--{boundary}\r\n'.encode())
        for header in headers:
            output.extend(header)
            output.extend(b'\r\n')
        output.extend(b'\r\n')
        output.extend(body)
        output.extend(b'\r\n')
    output.extend(f'--{boundary}--\r\n'.encode())
    return bytes(output)


@pytest.mark.asyncio
async def test_urlencoded_repeats_charset_and_empty_content_type() -> None:
    request, receive = make_request(
        method='POST',
        headers=((b'content-type', b'application/x-www-form-urlencoded'),),
        body_chunks=[b'a=1&a=2&b='],
    )
    result = await request.post()
    assert result.getall('a') == ['1', '2']
    assert result['b'] == ''
    assert await request.post() is result
    assert receive.calls == 1

    encoded = ('x=' + quote('привет', encoding='cp1251')).encode('ascii')
    request, _ = make_request(
        method='POST',
        headers=((b'content-type', b'application/x-www-form-urlencoded; charset=windows-1251'),),
        body_chunks=[encoded],
    )
    assert (await request.post())['x'] == 'привет'

    request, _ = make_request(
        method='POST',
        headers=((b'content-type', b''),),
        body_chunks=[b'x=empty-content-type'],
    )
    assert (await request.post())['x'] == 'empty-content-type'


@pytest.mark.asyncio
async def test_multipart_text_binary_file_and_repeated_fields() -> None:
    boundary = 'boundary-05'
    body = multipart_body(
        boundary,
        [
            ([b'Content-Disposition: form-data; name="text"'], b'hello'),
            (
                [
                    b'Content-Disposition: form-data; name="binary"',
                    b'Content-Type: application/octet-stream',
                ],
                b'\x00\x01',
            ),
            (
                [
                    b'Content-Disposition: form-data; name="upload"; filename="f.bin"',
                    b'Content-Type: application/pdf',
                    b'X-Part: yes',
                ],
                b'file-content',
            ),
            ([b'Content-Disposition: form-data; name="text"'], b'again'),
        ],
    )
    request, receive = make_request(
        method='POST',
        headers=((b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),),
        body_chunks=[body],
    )

    result = await request.post()
    assert result.getall('text') == ['hello', 'again']
    assert result['binary'] == b'\x00\x01'
    uploaded = result['upload']
    assert isinstance(uploaded, FileField)
    assert uploaded.name == 'upload'
    assert uploaded.filename == 'f.bin'
    assert uploaded.file.read() == b'file-content'
    assert uploaded.content_type == 'application/pdf'
    assert isinstance(uploaded.headers, CIMultiDictProxy)
    assert uploaded.headers['x-part'] == 'yes'
    assert await request.post() is result
    assert receive.calls == 1
    uploaded.file.close()


@pytest.mark.asyncio
async def test_file_defaults_and_utf8_filename() -> None:
    boundary = 'boundary-file'
    body = multipart_body(
        boundary,
        [
            (
                ['Content-Disposition: form-data; name="upload"; filename="файл.txt"'.encode()],
                b'data',
            )
        ],
    )
    request, _ = make_request(
        method='POST',
        headers=((b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),),
        body_chunks=[body],
    )
    uploaded = (await request.post())['upload']
    assert isinstance(uploaded, FileField)
    assert uploaded.filename == 'файл.txt'
    assert uploaded.content_type == 'application/octet-stream'
    uploaded.file.close()


@pytest.mark.asyncio
async def test_multipart_structure_errors() -> None:
    request, _ = make_request(
        method='POST',
        headers=((b'content-type', b'multipart/form-data'),),
        body_chunks=[b''],
    )
    with pytest.raises(ValueError, match='boundary missed'):
        await request.post()

    boundary = 'missing-name'
    request, _ = make_request(
        method='POST',
        headers=((b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),),
        body_chunks=[
            multipart_body(boundary, [([b'Content-Disposition: form-data'], b'value')])
        ],
    )
    with pytest.raises(ValueError, match='Multipart field missing name'):
        await request.post()


@pytest.mark.asyncio
async def test_urlencoded_total_size_uses_client_max_size() -> None:
    request, _ = make_request(
        method='POST',
        app=Rapidy(client_max_size=5),
        headers=((b'content-type', b'application/x-www-form-urlencoded'),),
        body_chunks=[b'x=1234567890'],
    )
    with pytest.raises(HTTPRequestEntityTooLarge):
        await request.post()


@pytest.mark.asyncio
async def test_multipart_total_size_uses_independent_limit() -> None:
    boundary = 'limit'
    body = multipart_body(boundary, [([b'Content-Disposition: form-data; name="x"'], b'large')])
    request, _ = make_request(
        method='POST',
        app=Rapidy(
            client_max_size=5,
            multipart_limits=replace(MultipartLimits(), max_body_size=len(body) - 1),
        ),
        headers=((b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),),
        body_chunks=[body],
    )
    with pytest.raises(HTTPRequestEntityTooLarge) as exc_info:
        await request.post()
    assert exc_info.value.max_size == len(body) - 1
    assert exc_info.value.actual_size == len(body)
    assert exc_info.value.text is not None
    assert 'multipart body size' in exc_info.value.text


@pytest.mark.asyncio
async def test_multipart_can_exceed_raw_body_limit_without_disabling_it() -> None:
    boundary = 'independent-limit'
    body = multipart_body(boundary, [([b'Content-Disposition: form-data; name="x"'], b'large')])
    request, receive = make_request(
        method='POST',
        app=Rapidy(client_max_size=5),
        headers=((b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),),
        body_chunks=[body[:17], body[17:41], body[41:]],
    )

    assert (await request.post())['x'] == 'large'
    assert receive.calls == 3
    assert request._read_bytes is None
    with pytest.raises(HTTPRequestEntityTooLarge) as exc_info:
        await request.read()
    assert exc_info.value.max_size == 5
    assert exc_info.value.actual_size == len(body)


@pytest.mark.asyncio
async def test_multipart_raw_body_and_files_spool_past_memory_threshold() -> None:
    boundary = 'disk-spool'
    body = multipart_body(
        boundary,
        [([b'Content-Disposition: form-data; name="file"; filename="f.bin"'], b'0123456789abcdef')],
    )
    request, _ = make_request(
        method='POST',
        app=Rapidy(multipart_limits=replace(MultipartLimits(), spool_threshold=8)),
        headers=((b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),),
        body_chunks=[body[:11], body[11:]],
    )

    uploaded = (await request.post())['file']
    assert isinstance(uploaded, FileField)
    assert request._body_file is not None
    assert cast('Any', request._body_file)._rolled is True
    assert cast('Any', uploaded.file)._rolled is True
    uploaded.file.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('limits', 'parts', 'message', 'maximum', 'actual'),
    [
        (
            replace(MultipartLimits(), max_parts=1),
            [
                ([b'Content-Disposition: form-data; name="one"'], b'1'),
                ([b'Content-Disposition: form-data; name="two"'], b'2'),
            ],
            'part count',
            1,
            2,
        ),
        (
            replace(MultipartLimits(), max_fields=1),
            [
                ([b'Content-Disposition: form-data; name="one"'], b'1'),
                ([b'Content-Disposition: form-data; name="two"'], b'2'),
            ],
            'field count',
            1,
            2,
        ),
        (
            replace(MultipartLimits(), max_files=1),
            [
                ([b'Content-Disposition: form-data; name="one"; filename="1.txt"'], b'1'),
                ([b'Content-Disposition: form-data; name="two"; filename="2.txt"'], b'2'),
            ],
            'file count',
            1,
            2,
        ),
        (
            replace(MultipartLimits(), max_field_size=3),
            [([b'Content-Disposition: form-data; name="field"'], b'1234')],
            'field size',
            3,
            4,
        ),
        (
            replace(MultipartLimits(), max_file_size=3),
            [([b'Content-Disposition: form-data; name="file"; filename="f.txt"'], b'1234')],
            'file size',
            3,
            4,
        ),
    ],
)
async def test_multipart_resource_limits(
    limits: MultipartLimits,
    parts: list[tuple[list[bytes], bytes]],
    message: str,
    maximum: int,
    actual: int,
) -> None:
    boundary = 'resource-limit'
    request, _ = make_request(
        method='POST',
        app=Rapidy(multipart_limits=limits),
        headers=((b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),),
        body_chunks=[multipart_body(boundary, parts)],
    )

    with pytest.raises(HTTPRequestEntityTooLarge) as exc_info:
        await request.post()
    assert exc_info.value.max_size == maximum
    assert exc_info.value.actual_size == actual
    assert exc_info.value.text is not None
    assert message in exc_info.value.text


@pytest.mark.parametrize(
    ('field', 'value', 'exception'),
    [
        ('max_body_size', 0, ValueError),
        ('max_parts', -1, ValueError),
        ('max_files', True, TypeError),
        ('spool_threshold', '1', TypeError),
    ],
)
def test_multipart_limits_validate_positive_integers(
    field: str,
    value: object,
    exception: type[Exception],
) -> None:
    with pytest.raises(exception, match=field):
        replace(MultipartLimits(), **cast('Any', {field: value}))


@pytest.mark.asyncio
async def test_post_gates_and_shared_read_cache() -> None:
    request, _ = make_request(
        method='GET',
        headers=((b'content-type', b'application/x-www-form-urlencoded'),),
        body_chunks=[b'x=1'],
    )
    result = await request.post()
    assert isinstance(result, MultiDictProxy)
    assert not result

    request, _ = make_request(
        method='POST',
        headers=((b'content-type', b'text/plain'),),
        body_chunks=[b'x=1'],
    )
    assert not await request.post()

    request, receive = make_request(
        method='POST',
        headers=((b'content-type', b'application/x-www-form-urlencoded'),),
        body_chunks=[b'x=1'],
    )
    assert await request.read() == b'x=1'
    assert (await request.post())['x'] == '1'
    assert receive.calls == 1

    request, receive = make_request(
        method='POST',
        headers=((b'content-type', b'application/x-www-form-urlencoded'),),
        body_chunks=[b'x=1'],
    )
    assert (await request.post())['x'] == '1'
    assert await request.read() == b'x=1'
    assert receive.calls == 1
