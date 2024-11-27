from enum import Enum

__all__ = [
    'ContentType',
    'Charset',
    'HeaderName',
]


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return str(self)


class ContentType(StrEnum):
    """Content-Type header.

    If you couldn't find what you need, but you really want to see it here, form `issue` here:
        https://github.com/rAPIdy-org/rAPIdy/issues/new

    The main list is provided here:
        https://www.iana.org/assignments/media-types/media-types.xhtml
    """

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
    m_part_related = 'multipart/related'  # using by MHTML (HTML mail)
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


class Charset(StrEnum):
    """Charset.

    If you couldn't find what you need, but you really want to see it here, form `issue` here:
        https://github.com/rAPIdy-org/rAPIdy/issues/new
    """

    utf8 = 'utf-8'
    utf16 = 'utf-16'
    utf32 = 'utf-32'


class HeaderName(StrEnum):
    """Header name.

    If you couldn't find what you need, but you really want to see it here, form `issue` here:
        https://github.com/rAPIdy-org/rAPIdy/issues/new
    """

    accept = 'Accept'
    accept_charset = 'Accept-Charset'
    accept_encoding = 'Accept-Encoding'
    accept_language = 'Accept-Language'
    accept_ranges = 'Accept-Ranges'
    access_control_max_age = 'Access-Control-Max-Age'
    access_control_allow_credentials = 'Access-Control-Allow-Credentials'
    access_control_allow_headers = 'Access-Control-Allow-Headers'
    access_control_allow_methods = 'Access-Control-Allow-Methods'
    access_control_allow_origin = 'Access-Control-Allow-Origin'
    access_control_expose_headers = 'Access-Control-Expose-Headers'
    access_control_request_headers = 'Access-Control-Request-Headers'
    access_control_request_method = 'Access-Control-Request-Method'
    age = 'Age'
    allow = 'Allow'
    authorization = 'Authorization'

    cache_control = 'Cache-Control'
    connection = 'Connection'
    content_disposition = 'Content-Disposition'
    content_encoding = 'Content-Encoding'
    content_language = 'Content-Language'
    content_length = 'Content-Length'
    content_location = 'Content-Location'
    content_md5 = 'Content-MD5'
    content_range = 'Content-Range'
    content_transfer_encoding = 'Content-Transfer-Encoding'
    content_type = 'Content-Type'
    cookie = 'Cookie'

    date = 'Date'
    destination = 'Destination'
    digest = 'Digest'

    etag = 'Etag'
    expect = 'Expect'
    expires = 'Expires'

    forwarded = 'Forwarded'
    from_ = 'From'

    host = 'Host'

    if_match = 'If-Match'
    if_modified_since = 'If-Modified-Since'
    if_none_match = 'If-None-Match'
    if_range = 'If-Range'
    if_unmodified_since = 'If-Unmodified-Since'

    keep_alive = 'Keep-Alive'

    last_event_id = 'Last-Event-ID'
    last_modified = 'Last-Modified'
    link = 'Link'
    location = 'Location'

    max_forwards = 'Max-Forwards'

    origin = 'Origin'

    pragma = 'Pragma'
    proxy_authenticate = 'Proxy-Authenticate'
    proxy_authorization = 'Proxy-Authorization'

    range = 'Range'
    referer = 'Referer'
    retry_after = 'Retry-After'

    sec_websocket_accept = 'Sec-WebSocket-Accept'
    sec_websocket_version = 'Sec-WebSocket-Version'
    sec_websocket_protocol = 'Sec-WebSocket-Protocol'
    sec_websocket_extensions = 'Sec-WebSocket-Extensions'
    sec_websocket_key = 'Sec-WebSocket-Key'
    sec_websocket_key1 = 'Sec-WebSocket-Key1'
    server = 'Server'
    set_cookie = 'Set-Cookie'

    te = 'TE'
    trailer = 'Trailer'
    transfer_encoding = 'Transfer-Encoding'

    upgrade = 'Upgrade'
    uri = 'URI'
    user_agent = 'User-Agent'

    vary = 'Vary'
    via = 'Via'

    want_digest = 'Want-Digest'
    warning = 'Warning'
    www_authenticate = 'WWW-Authenticate'

    x_forwarded_for = 'X-Forwarded-For'
    x_forwarded_host = 'X-Forwarded-Host'
    x_forwarded_proto = 'X-Forwarded-Proto'


class HTTPRequestParamType(StrEnum):
    path = 'path'
    query = 'query'
    header = 'header'
    cookie = 'cookie'
    body = 'body'
