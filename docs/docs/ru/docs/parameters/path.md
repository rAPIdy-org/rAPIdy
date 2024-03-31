# Path parameters
Path-параметры позволяют строить **динамические маршруты** внутри вашего приложения.

Вы можете определить path-параметры используя синтаксис форматированных строк Python:

!!! example ""
    ```Python hl_lines="1"
    @routes.get('/{user_id}')
    async def handler(...) -> web.Response:
        ...
    ```
    
    ```Python hl_lines="4"
    async def handler(...) -> web.Response:
        ...
    
    route = web.get('/{user_id}', handler)
    ```
    !!! tip "Примеры обработчиков для каждого типа данных [<code>Path</code>](#path) [<code>PathSchema</code>](#pathschema) [<code>PathRaw</code>](#pathraw)"
    

## Типы данных
### Path
!!! tip "Рекомендованный параметр для этого типа данных"

Path-параметр используется тогда, когда вам необходимо точечно извлекать поступающие данные.

!!! example "Первый способ"
    ```Python hl_lines="7 10"
    {!> ./parameters/path/types/Path/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        В браузере перейдите по адресу: <a href="http://127.0.0.1:8080/user_1" target="blank">http://127.0.0.1:8080/user_1</a>
        или отправьте запрос с помощью `curl`:
        ```
        curl -X GET http://127.0.0.1:8080/user_1
        ```
        вы получите ответ:
        ```
        {"user_id": "user_1"}
        ```

??? example "Несколько параметров <code>Path</code>"
    ```Python hl_lines="7 10 11"
    {!> ./parameters/path/types/Path/ex_02.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        В браузере перейдите по адресу:  <a href="http://127.0.0.1:8080/user_1/param_2" target="blank">http://127.0.0.1:8080/user_1/param_2</a>
        или отправьте запрос с помощью `curl`:
        ```
        curl -X GET http://127.0.0.1:8080/user_1/param_2
        ```
        вы получите ответ:
        ```
        {"user_id": "user_1", "some_param", "param_2"}
        ```


### PathSchema
PathSchema-параметр удобен тогда, когда вам нужно извлекать большое количество данных.

!!! tip ""
    Маловероятно, что вы будете использовать этот тип по причине того, что в Path обычно передаются не более 1-2 параметров, но для 
    единообразия данный тип существует.

!!! example "<code>PathSchema</code>"
    ```Python hl_lines="9 11 14"
    {!> ./parameters/path/types/PathSchema/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        В браузере перейдите по адресу: <a href="http://127.0.0.1:8080/user_1" target="blank">http://127.0.0.1:8080/user_1</a>
        или отправьте запрос с помощью `curl`:
        ```
        curl -X GET http://127.0.0.1:8080/user_1
        ```
        вы получите ответ:
        ```
        {"user_id": "user_1"}
        ```

??? example "<code>PathSchema</code> с несколькими параметрами"
    ```Python hl_lines="9 10 12 15"
    {!> ./parameters/path/types/PathSchema/ex_02.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        В браузере перейдите по адресу:  <a href="http://127.0.0.1:8080/user_1/param_2" target="blank">http://127.0.0.1:8080/user_1/param_2</a>
        или отправьте запрос с помощью `curl`:
        ```
        curl -X GET http://127.0.0.1:8080/user_1/param_2
        ```
        вы получите ответ:
        ```
        {"user_id": "user_1", "some_param", "param_2"}
        ```

### PathRaw
PathRaw-параметр используется тогда, когда вам требуется извлечь данные как есть.

!!! example "<code>PathRaw</code>"
    ```Python hl_lines="8 11"
    {!> ./parameters/path/types/PathRaw/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        В браузере перейдите по адресу: <a href="http://127.0.0.1:8080/user_1" target="blank">http://127.0.0.1:8080/user_1</a>
        или отправьте запрос с помощью `curl`:
        ```
        curl -X GET http://127.0.0.1:8080/user_1
        ```
        вы получите ответ:
        ```
        {"path": {"user_id": "user_1"}}
        ```

??? example "PathRaw с несколькими параметрами"
    ```Python hl_lines="8 11"
    {!> ./parameters/path/types/PathRaw/ex_02.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        В браузере перейдите по адресу: <a href="http://127.0.0.1:8080/user_1/param_2" target="blank">http://127.0.0.1:8080/user_1/param_2</a>
        или отправьте запрос с помощью `curl`:
        ```
        curl -X GET http://127.0.0.1:8080/user_1/param_2
        ```
        вы получите ответ:
        ```
        {"path": {"user_id": "user_1", "some_param": "param_2"}}
        ```

!!! warning "Внимание"
    PathRaw не использует валидацию pydantic. Все данные содержащиеся в типе извлекаются как есть.
    Подробнее см. в разделе [Raw data](../raw_data.md).

## Ключевые особенности
### Поддержка регулярных выражений
Переменные пути имеют поддержку регулярных выражений
<i>(источник: <a href="https://docs.aiohttp.org/en/stable/web_quickstart.html" target="blank">aiohttp quickstart</a> раздел <b><span class="note-color">Resources and Routes</span></b>).</i>

По умолчанию каждый параметр пути соответствует регулярному выражению `[^{}/]+`.

Вы также можете указать собственное регулярное выражение в форме `{<path_variable>:<regex>}`.

!!! example ""
    ```Python hl_lines="1"
    @routes.get('/{user_id:\d+}')
    async def handler(...) -> web.Response:
        ...
    ```

    ```Python hl_lines="4"
    async def handler(...) -> web.Response:
        ...

    route = web.get(r'/{name:\d+}', handler
    ```

### Использование именованных ресурсов
!!! tip "Подробнее о именованных ресурсах [Named resources](../named_resources.md)"

!!! example "Пример перенаправления с предопределенным <code>Path-параметром</code>"
    ```python hl_lines="7 17 18"
    {!> ./parameters/path/named_resource/ex_01.py !}
    ```
    ??? tip "Пример запроса"
        Скопируйте пример в файл `main.py` и запустите `python3 main.py`.<br/>
        В браузере если вы перейдите по адресу: <a href="http://127.0.0.1:8080" target="blank">http://127.0.0.1:8080</a>, то вас перенаправит на
        ```
        http://127.0.0.1:8080/get_user_info/user_1
        ```
        вы получите ответ:
        ```
        {"path": {"user_id": "user_1", "some_param": "param_2"}}
        ```

### Значения по умолчанию
Поскольку Path-параметр составляет часть пути он является обязательным и не может быть заменен значением по умолчанию.

!!! warning "В случае запуска сервера со значением по умолчанию для любого Path-параметра, будет поднято исключение"

!!! failure "Ошибка"
    ??? note "Попытка задать значение по умолчанию для <code>Path</code>"
        ```python hl_lines="4"
        @routes.get('/{user_id}')
        async def handler(
                request: web.Request,
                user_id: Annotated[str, Path] = 'user_1',
        ) ->  web.Response:
        ```
    ??? note "Попытка задать значение по умолчанию для <code>PathSchema</code>" 
        ```python hl_lines="7"
        class PathRequestSchema(BaseModel):
            user_id: str
    
        @routes.get('/{user_id}')
        async def handler(
                request: web.Request,
                path: Annotated[PathRequestSchema, PathSchema] = PathRequestSchema(user_id='user_1'),
        ) -> web.Response:
        ```
    ??? note "Попытка задать значение по умолчанию для <code>PathRaw</code>"
        ```python hl_lines="4"
        @routes.get('/{user_id}')
        async def handler(
                request: web.Request,
                path: Annotated[PathRequestSchema, PathSchema] = {'user_id': 'user_1'},
        ) -> web.Response:
        ```

    ```python
    AssertionError: Handler attribute with Type `Path` cannot have a default value.
    Handler path: `<path to file>/main.py`.
    Handler name: `handler`.
    Attribute name: `user_id`.
    ```

!!! warning "Предупреждение"
    Для `PathRequestSchema` есть вариант передать значение по умолчанию, через `pydantic.Field`.<br/>
    К сожалению, в виду технических ограничений, этот сценарий не вызовет исключения, поэтому он просто игнорируется.

    ```python hl_lines="2 7"
    class PathRequestSchema(BaseModel):
        user_id: str = Field('user_1')

    @routes.get('/{user_id}')
    async def handler(
            request: web.Request,
            path: Annotated[PathRequestSchema, PathSchema],
    ) -> web.Response:
        return web.json_response({'user_id': path.user_id})
    ```
    
    Если у вас запущен сервер по адресу `http://127.0.0.1:8080` и вы перейдете по <a href="http://127.0.0.1:8080/" target="blank">http://127.0.0.1:8080/</a>, то получите в ответе `404: Not Found`.


!!! tip ""
    Подробнее о значениях по умолчанию см в разделе [Default values](../default_values.md)