from rapidy.request_params import Path, PathRaw, PathSchema

Path('1')
Path(default_factory=lambda: '1')
Path('1', default_factory=lambda: '1')

PathSchema('1')
PathSchema(default_factory=lambda: '1')
PathSchema('1', default_factory=lambda: '1')

PathRaw('1')
PathRaw(default_factory=lambda: '1')
PathRaw('1', default_factory=lambda: '1')
