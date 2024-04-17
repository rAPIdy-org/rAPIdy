from rapidy.request_params import StreamBody

StreamBody('1')
StreamBody(default_factory=lambda: '1')
StreamBody('1', default_factory=lambda: '1')
