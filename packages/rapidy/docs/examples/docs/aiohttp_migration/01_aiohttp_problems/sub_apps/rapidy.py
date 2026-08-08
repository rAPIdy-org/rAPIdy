from rapidy import Rapidy
from rapidy.http import HTTPRouter

v1_app = HTTPRouter('/v1')
rapidy = Rapidy(http_route_handlers=[v1_app])