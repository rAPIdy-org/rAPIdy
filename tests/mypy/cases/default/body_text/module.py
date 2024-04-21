from rapidy.request_params import TextBody

TextBody('1')
TextBody(default_factory=lambda: '1')
TextBody('1', default_factory=lambda: '1')
