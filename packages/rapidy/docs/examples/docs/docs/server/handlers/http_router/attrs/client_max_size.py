from rapidy.http import HTTPRouter

router = HTTPRouter(
    path='/api',
    client_max_size=1000,
)