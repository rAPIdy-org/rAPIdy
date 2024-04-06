from rapidy.request_params import FormDataBody, FormDataBodyRaw, FormDataBodySchema

FormDataBody('1')
FormDataBody(default_factory=lambda: '1')
FormDataBody('1', default_factory=lambda: '1')

FormDataBodySchema('1')
FormDataBodySchema(default_factory=lambda: '1')
FormDataBodySchema('1', default_factory=lambda: '1')

FormDataBodyRaw('1')
FormDataBodyRaw(default_factory=lambda: '1')
FormDataBodyRaw('1', default_factory=lambda: '1')
