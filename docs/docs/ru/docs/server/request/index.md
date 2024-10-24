# Request
**Веб-запрос** — это запрос, сделанный клиентом, например веб-браузером, к серверу для получения веб-страницы или 
другого ресурса. 

Данный раздел покажет, как можно извлекать и проверять данные из входящего Веб-запроса используя **`Rapidy`**.

!!! tip "Более детальные сценарии применения вы найдете в примерах - **[Examples](../../../../examples.md)**."

## Получение данных с помощью параметров
Вы можете извлечь и проверить с помощью `pydantic` любой параметр http-запроса используя функционал `Rapidy`.

!!! info "Извлеките параметр из модуля `rapidy.request_parameters` или из модуля `rapidy.web`." 
    ```python
    from rapidy import web
    from rapidy.request_parameters import PathParam, Header, Cookie, QueryParam, Body
    
    routes = web.RouteTableDef()

    @routes.get('/{user_id}')
    async def handler(
        user_id: int = PathParam(),
        host: str = Header(alias='Host'),
        session: str = Cookie(alias='UserSession'),
        age_filter: str = QueryParam(alias='AgeFilter'),
        data: str = Body(),
    ) -> ...:
    ```
    или
    ```python
    from rapidy import web

    routes = web.RouteTableDef()

    @routes.get('/{user_id}')
    async def handler(
        user_id: int = web.PathParam(),
        host: str = web.Header(alias='Host'),
        session: str = web.Cookie(alias='UserSession'),
        age_filter: str = web.QueryParam(alias='AgeFilter'),
        data: str = web.Body(),
    ) -> ...:
    ```

!!! tip "Более подробно о том как это работает вы можете прочитать в разделе - **[Parameters](parameters)**"

## Получение данных с помощью объекта запроса
Вы можете извлечь данные напрямую из объекта запроса `web.Request`, для этого добавьте его как аттрибут в ваш 
http-обработчик.

```python
from rapidy import web

routes = web.RouteTableDef()

@routes.get('/{user_id}')
async def handler(
    request: web.Request,
) -> ...:
    path_params = request.match_info  # dict[str, str]
    headers = request.headers  # CIMultiDictProxy[str]
    cookies = request.cookies  # Mapping[str, str]
    query_params = request.rel_url.query  # MultiDictProxy[str]
    json_body = await request.json()  # Any
    text_body = await request.text()  # str
    bytes_body = await request.read()  # bytes
    stream_body = request.content  # StreamReader
```

!!! note "Если у аттрибута обработчика указан тип `Request`, то не важно какой это аттрибут по порядку."
    ```python
    from rapidy import web
    
    routes = web.RouteTableDef()
    
    @routes.get('/')
    async def handler(
        host: str = web.Header(alias='Host'),
        request: web.Request,
    ) -> ...:
    ```


!!! warning "При отсутствии типа у первого аттрибута обработчика`Rapidy`автоматический подставит в него `Request`."
    ```python
    from rapidy import web
    
    routes = web.RouteTableDef()
    
    @routes.get('/')
    async def handler(
        any_attr,
    ) -> ...:
        print(type(any_attr))
        # web.Request
    ```

!!! note "Rapidy использует встроенные механизмы извлечения данных `aiohttp`"
    Подробнее об объекте `aiohttp.web.Request` и способов извлечения из него данных можно ознакомиться 
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.
