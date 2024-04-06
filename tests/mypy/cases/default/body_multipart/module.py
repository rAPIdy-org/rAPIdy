from rapidy.request_params import MultipartBody, MultipartBodyRaw, MultipartBodySchema

MultipartBody('1')
MultipartBody(default_factory=lambda: '1')
MultipartBody('1', default_factory=lambda: '1')

MultipartBodySchema('1')
MultipartBodySchema(default_factory=lambda: '1')
MultipartBodySchema('1', default_factory=lambda: '1')

MultipartBodyRaw('1')
MultipartBodyRaw(default_factory=lambda: '1')
MultipartBodyRaw('1', default_factory=lambda: '1')
