# Binary
Чтение тела запроса в виде последовательности байт.

## Описание
**Binary** (MIME-type: `application/octet-stream`) — двоичный тип данных.

!!! info "`Rapidy` позволяет извлекать любые данные с `content_type` в виде последовательности байт."
    Просто укажите аннотацию `bytes` или `StreamReader`.

    !!! tip "Зачем это нужно?"
        Это полезно, если нужно явно ограничить тип принимаемых данных и затем обработать их в двоичном виде.

!!! info "Есть только два типа данных, которые можно извлекать без учета `content_type`: `bytes` и `StreamReader`."

---

## bytes
```python
{!> ./docs/docs/server/request/parameters/body/binary/01_extract_bytes.py !}
```

## StreamReader
!!! note "Подробнее об объекте `StreamReader` можно узнать **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">здесь</a>**."

```python
{!> ./docs/docs/server/request/parameters/body/binary/02_extract_stream_reader.py !}
```

---

## Извлечение без валидации
!!! warning "Эти способы не рекомендуются."
    Если отключить валидацию, параметр вернет базовую структуру `aiohttp`:

    - `Body(content_type=ContentType.stream)` → `bytes`

!!! warning "Валидация `pydantic` для `StreamReader` не работает."

### Способы отключения валидации

!!! info "Отключение валидации с `validate=False`"
    Установите `Body(validate=False)`.
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/03_ignore_validation/01_validate_attr_false.py !}
    ```

!!! info "Отключение через `Any`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/03_ignore_validation/02_any_type.py !}
    ```

!!! info "Отключение типизации"
    Если не указывать тип, по умолчанию будет использован `Any`.
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/03_ignore_validation/03_no_type.py !}
    ```

---

## Значения по умолчанию
Если HTTP-запрос не содержит тела, параметр получит указанное значение по умолчанию (если оно задано).

### Примеры использования

#### Указано значение по умолчанию
```python
{!> ./docs/docs/server/request/parameters/body/binary/04_default/01_default_exists.py !}
```

#### Опциональное тело запроса
```python
{!> ./docs/docs/server/request/parameters/body/binary/04_default/02_default_optional.py !}
```

??? warning "Значение по умолчанию для `StreamReader` задать нельзя."
    Если попытаться установить `default` или `default_factory` для `StreamReader`, будет вызвана ошибка `ParameterCannotUseDefaultError`.
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/04_default/03_stream_reader_cant_default.py !}
    ```
    ```text
    {!> ./docs/docs/server/request/parameters/body/binary/04_default/03_stream_reader_cant_default_text.txt !}
    ```

---

## Как извлекаются сырые данные
!!! note "`Rapidy` использует встроенные механизмы `aiohttp`."
    Подробнее о `aiohttp.Request` и методах извлечения данных можно прочитать **<a href='https://docs.aiohttp.org/en/stable/web_reference.html' target='_blank'>здесь</a>**.

### bytes
`Rapidy` вызывает метод `read` объекта `Request`, а затем передает полученные данные в `pydantic` для валидации.

!!! info "Как работает извлечение в `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/05_rapidy_extract_data_binary.py !}
    ```

### StreamReader
`Rapidy` использует атрибут `content` объекта `Request` и передает его напрямую в обработчик запроса, минуя валидацию `pydantic`.

!!! info "Как работает извлечение в `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/binary/06_rapidy_extract_data_stream_reader.py !}
    ```
