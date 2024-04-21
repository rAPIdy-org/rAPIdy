from rapidy.request_params import BytesBody

BytesBody('1')
BytesBody(default_factory=lambda: '1')
BytesBody('1', default_factory=lambda: '1')
