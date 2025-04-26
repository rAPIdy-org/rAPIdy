from rapidy import Rapidy
from rapidy.web import View
from rapidy.depends import FromDI
from .providers import FooProvider

class FooView(View):
    async def get(self, c: FromDI[int]) -> dict:
        return {"value": c}

app = Rapidy(di_providers=[FooProvider()])
app.router.add_view('/', FooView)