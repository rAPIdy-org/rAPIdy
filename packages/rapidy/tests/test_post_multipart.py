from __future__ import annotations

from urllib.parse import quote

import pytest
from multidict import CIMultiDictProxy, MultiDictProxy

from rapidy import Rapidy
from rapidy.exceptions import HTTPRequestEntityTooLarge
from rapidy.request import FileField
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
@pytest.mark.parametrize(
    ('content_type', 'body'),
    [
        ('application/x-www-form-urlencoded', b'x=1234567890'),
        (
            'multipart/form-data; boundary=limit',
            multipart_body('limit', [([b'Content-Disposition: form-data; name="x"'], b'large')]),
        ),
    ],
)
async def test_form_total_size_limit(content_type: str, body: bytes) -> None:
    request, _ = make_request(
        method='POST',
        app=Rapidy(client_max_size=5),
        headers=((b'content-type', content_type.encode()),),
        body_chunks=[body],
    )
    with pytest.raises(HTTPRequestEntityTooLarge):
        await request.post()


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
