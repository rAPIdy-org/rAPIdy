# Enums

## Description
`Rapidy` supports multiple types of enumerations, making the code more readable and maintainable.

Instead of using "magic" numbers or strings, clear and meaningful names are applied, which enhances code clarity and reduces the likelihood of errors.

!!! info "All enumerations (`enum`) are located in the `rapidy.enums` module."

## ContentType
`rapidy.enums.ContentType` — an enumeration containing commonly used `MIME types`.

```python
class ContentType(str, Enum):
    any = '*/*'

    # application
    json = 'application/json'
    ldap = 'application/ld+json'
    app_xml = 'application/xml'
    zip = 'application/zip'
    pdf = 'application/pdf'
    stream = 'application/octet-stream'
    x_www_form = 'application/x-www-form-urlencoded'

    # text
    text_plain = 'text/plain'
    text_html = 'text/html'
    text_css = 'text/css'
    text_csv = 'text/csv'
    text_js = 'text/javascript'
    text_xml = 'text/xml'
    text_any = 'text/*'

    # multipart
    m_part_mixed = 'multipart/mixed'
    m_part_alt = 'multipart/alternative'
    m_part_related = 'multipart/related'  # used by MHTML (HTML mail)
    m_part_form_data = 'multipart/form-data'

    # image
    img_jpeg = 'image/jpeg'
    img_png = 'image/png'
    img_gif = 'image/gif'
    img_tiff = 'image/tiff'
    img_x_ico = 'image/x-icon'
    img_ms_ico = 'image/vnd.microsoft.icon'
    img_svg_xml = 'image/svg+xml'
    img_vnd_djvu = 'image/vnd.djvu'

    # audio
    audio_mpeg = 'audio/mpeg'
    audio_x_ms_wma = 'audio/x-ms-wma'
    audio_x_wav = 'audio/x-wav'

    # video
    video_mpeg = 'video/mpeg'
    video_mp4 = 'video/mp4'
    video_quicktime = 'video/quicktime'
    video_x_ms_wmv = 'video/x-ms-wmv'
    video_x_flv = 'video/x-flv'
    video_webm = 'video/webm'
```

!!! tip "Couldn't find what you were looking for?"
    If you couldn't find the `MIME type` you need, you can specify it as a string *(`application/some-type`)* or
    suggest adding it to `ContentType` **<a href="https://github.com/rAPIdy-org/rAPIdy/issues/new" target="_blank">here</a>**.

## Charset
`rapidy.enums.Charset` — an enumeration containing commonly used character encodings (`charset`).

```python
class Charset(str, Enum):
    utf8 = 'utf-8'
    utf16 = 'utf-16'
    utf32 = 'utf-32'
```

!!! tip "Couldn't find the encoding you need?"
    If the required encoding is not listed, you can specify it as a string *(`utf-8`)*
    or suggest adding it to `Charset` **<a href="https://github.com/rAPIdy-org/rAPIdy/issues/new" target="_blank">here</a>**.

## HeaderName
`rapidy.enums.HeaderName` — an enumeration containing commonly used HTTP header names.

```python
class HeaderName(str, Enum):
    content_type = 'Content-Type'
    content_length = 'Content-Length'
    content_encoding = 'Content-Encoding'
    content_language = 'Content-Language'
    content_location = 'Content-Location'
    content_md5 = 'Content-MD5'
    content_range = 'Content-Range'
    expires = 'Expires'
    last_modified = 'Last-Modified'

    host = 'Host'
    user_agent = 'User-Agent'
    cookie = 'Cookie'

    etag = 'ETag'
    location = 'Location'
    server = 'Server'
    set_cookie = 'Set-Cookie'
    retry_after = 'Retry-After'

    authorization = 'Authorization'
    www_authenticate = 'WWW-Authenticate'
    proxy_authenticate = 'Proxy-Authenticate'
    proxy_authorization = 'Proxy-Authorization'
```

!!! tip "Couldn't find the header you need?"
    If the required header is not listed, you can specify it as a string *(`Awesome-Header`)*
    or suggest adding it to `HeaderName` **<a href="https://github.com/rAPIdy-org/rAPIdy/issues/new" target="_blank">here</a>**.
