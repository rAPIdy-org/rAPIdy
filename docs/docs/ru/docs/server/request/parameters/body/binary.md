# Binary

## Bytes
## StreamReader

## Как извлекаются сырые данные
Всего существует два типа данных, которые могут использовать аннотацию для извлечения данных.



аннотацию для извлечения данных, вместо  


у которых есть свой собственный извлекатель данных, это `StreamReader` и `bytes`. 
Оба типа работают с телом входящего запроса как с последовательностью байт и сверхсложное извлечение для них
не требуется.

`Rapidy` внутри себя использует вызов `post` объекта `Request`, а затем передает полученный объект на валидацию 
в `pydantic` модель.

!!! info "Как извлекаются данные внутри `Rapidy`"
    ```python
    async def extract_post_data(request: Request) -> Optional[MultiDictProxy[Union[str, bytes, FileField]]]:
        if not request.body_exists:
            return None
    
        return await request.post()
    ```

!!! note "Rapidy использует встроенные механизмы извлечения данных `aiohttp`"
    Подробнее об объекте `aiohttp.web.Request` и способов извлечения из него данных можно ознакомиться 
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

!!! note ""
    Извлечение данных для `x-www-form-urlencoded` и `multipart/form-data` происходит одинаково, через метод `post` объекта 
    `web.Request` -> это особенность реализации `aiohttp`.

