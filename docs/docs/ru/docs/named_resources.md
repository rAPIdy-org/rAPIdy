# Named resources

Каждый ваш `маршрут` может быть дополнен аттрибутом `name`.

<details open>
<summary>Первый способ</summary>

```python hl_lines="1"
@routes.get('/{user_id}', name='user_id_handler')
async def handler(
    request: web.Request,
    user_id: Annotated[str, Path],
) -> web.Response:
```
</details>

<details>
<summary>Второй способ</summary>

```python hl_lines="6"
async def handler(
    request: web.Request,
    user_id: Annotated[str, Path],
) -> web.Response:

app.add_routes([web.get('/{user_id}', handler, name='user_id_handler')])
```
</details>

В дальнейшем аттрибут `name` можно использовать для создания динамических URl-адресов с предопределенными значениями Path-переменных.

Это может быть необходимо, например, для перенаправления пользователя на другой ресурс.

!!! note "Пример перенаправления с предопределенным <code>Path-параметром</code>"
    ```python hl_lines="7 12 17 18"
    from typing_extensions import Annotated
    from rapidy import web
    from rapidy.request_params import Path
    
    routes = web.RouteTableDef()
    
    @routes.get('/get_user_info/{user_id}', name='user_info')
    async def get_user_info_handler(
        request: web.Request,
        user_id: Annotated[str, Path],
    ) -> web.Response:
        return web.json_response({'user_id': user_id})
    
    @routes.get('/')
    async def handler(request: web.Request) -> web.Response:
        user_id = 'user_1'
        router = request.app.router['user_info']
        url = router.url_for(user_id=user_id)
        return web.Response(status=302, headers={"Location": str(url)})
    
    app = web.Application()
    app.add_routes(routes)
    
    if __name__ == '__main__':
        web.run_app(app, host='127.0.0.1', port=8080)
    ```
    !!! tip "Примечание"
        При запущенном сервере переход по адресу: <a href="http://127.0.0.1:8080" target="blank">http://127.0.0.1:8080</a>, перенаправит вас 
        на `http://127.0.0.1:8080/get_user_info/user_1` с ответом: `{"user_id": "user_1"}`.

!!! note "Пример перенаправления с предопределенным <code>Query-параметром</code>"
    ```python hl_lines="7 10 17 18"
    from typing_extensions import Annotated
    from rapidy import web
    from rapidy.request_params import Query
    
    routes = web.RouteTableDef()
    
    @routes.get('/get_user_info', name='user_info')
    async def get_user_info_handler(
        request: web.Request,
        user_filter: Annotated[str, Query],
    ) -> web.Response:
        return web.json_response({'user_filter': user_filter})
    
    @routes.get('/')
    async def handler(request: web.Request) -> web.Response:
        user_filter = 'awesome_filter'
        router = request.app.router['user_info']
        url = router.url_for().with_query({'user_filter': user_filter})
        return web.Response(status=302, headers={"Location": str(url)})
    
    app = web.Application()
    app.add_routes(routes)
    
    if __name__ == '__main__':
        web.run_app(app, host='127.0.0.1', port=8080)
    ```
    !!! tip "Примечание"
        При запущенном сервере переход по адресу: <a href="http://127.0.0.1:8080" target="blank">http://127.0.0.1:8080</a>, перенаправит вас 
        на `http://127.0.0.1:8080/get_user_info?user_filter=awesome_filter` <br/>
        с ответом: `{"user_filter": "awesome_filter"}`.

!!! note "Пример перенаправления с предопределенным <code>Path-параметром</code> и <code>Query-параметром</code>"
    ```python hl_lines="7 10 11 19 20"
    from typing_extensions import Annotated
    from rapidy import web
    from rapidy.request_params import Path, Query
    
    routes = web.RouteTableDef()
    
    @routes.get('/get_user_info/{user_id}', name='user_info')
    async def get_user_info_handler(
        request: web.Request,
        user_id: Annotated[str, Path],
        user_filter: Annotated[str, Query],
    ) -> web.Response:
        return web.json_response({'user_id': user_id, 'user_filter': user_filter})
    
    @routes.get('/')
    async def handler(request: web.Request) -> web.Response:
        user_id = 'user_1'
        user_filter = 'awesome_filter'
        router = request.app.router['user_info']
        url = router.url_for(user_id=user_id).with_query({'user_filter': user_filter})
        return web.Response(status=302, headers={"Location": str(url)})
    
    app = web.Application()
    app.add_routes(routes)
    
    if __name__ == '__main__':
        web.run_app(app, host='127.0.0.1', port=8080)
    ```
    !!! tip "Примечание"
        При запущенном сервере переход по адресу: <a href="http://127.0.0.1:8080" target="blank">http://127.0.0.1:8080</a>, перенаправит вас 
        на `http://127.0.0.1:8080/get_user_info/user_1?user_filter=awesome_filter` <br/>
        с ответом: `{"user_id": "user_1", "user_filter": "awesome_filter"}`.

!!! tip "О редиректах"
    Вы также можете воспользоваться конструкцией `raise HTTPFound(url)` для того чтобы совершить редирект клиента.
    ```python hl_lines="9"
    from rapidy.web_exceptions import HTTPFound

    @routes.get('/{user_id}', name='user_id_handler')
    async def handler(
        request: web.Request,
        user_id: Annotated[str, Path],
    ) -> web.Response:
        url = request.app.router['user_info'].url_for(user_id=user_id)
        raise HTTPFound(url)
    ```
    !!! warning "Этот путь не является рекомендованным"
