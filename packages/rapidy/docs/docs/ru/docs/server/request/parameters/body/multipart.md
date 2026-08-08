# Multipart Form Data
Чтение тела запроса как `multipart/form-data`.

## Описание
**Form Data** *(MIME-type: `multipart/form-data`)* — один из наиболее часто используемых типов содержимого для передачи **двоичных** данных на сервер.

Формат *multipart* означает, что данные отправляются на сервер отдельными частями.
Каждая часть может иметь свой тип содержимого, имя файла и сами данные.
Разделение данных происходит с помощью граничной строки.

```python
{!> ./docs/docs/server/request/parameters/body/multipart/01_index/example.py !}
```

!!! example "Пример данных"
    ```text
    {!> ./docs/docs/server/request/parameters/body/multipart/01_index/raw_example.txt !}
    ```

??? example "Отправка с помощью `curl`"
    ```bash
    {!> ./docs/docs/server/request/parameters/body/multipart/01_index/curl.sh !}
    ```

---

## Извлечение без валидации

!!! warning "Отключение валидации не рекомендуется."
    Если валидация отключена, параметр будет содержать базовую структуру `aiohttp`:

    - `Body(content_type=ContentType.m_part_form_data) → MultiDictProxy[Union[str, bytes, FileField]]`

### Способы отключения валидации

#### Явное отключение
```python
{!> ./docs/docs/server/request/parameters/body/multipart/02_ignore_validation/01_validate_attr_false.py !}
```

#### Использование `Any`
```python
{!> ./docs/docs/server/request/parameters/body/multipart/02_ignore_validation/02_any_type.py !}
```

#### Отсутствие аннотации типа
Если не указывать тип, по умолчанию будет установлен `Any`.
```python
{!> ./docs/docs/server/request/parameters/body/multipart/02_ignore_validation/03_no_type.py !}
```

---

## Значения по умолчанию
Если HTTP-запрос не содержит тела, параметр получит указанное значение по умолчанию (если оно задано).

### Примеры использования

#### Указано значение по умолчанию
```python
{!> ./docs/docs/server/request/parameters/body/multipart/03_default/01_default_exists.py !}
```

#### Опциональное тело запроса
```python
{!> ./docs/docs/server/request/parameters/body/multipart/03_default/02_default_optional.py !}
```

---

## Извлечение сырых данных
`Rapidy` использует метод `post` объекта `Request` для получения данных и передает их в `Pydantic` для валидации.

??? info "Как происходит извлечение внутри `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/01_extract_raw.py !}
    ```

!!! note "`Rapidy` использует встроенные механизмы `aiohttp`"
    Подробнее об объекте `aiohttp.Request` и методах извлечения данных можно узнать
    **<a href="https://docs.aiohttp.org/en/stable/web_reference.html" target="_blank">здесь</a>**.

!!! note "`x-www-form-urlencoded` и `multipart/form-data` обрабатываются одинаково."
    Оба этих типа данных извлекаются через метод `post` объекта `Request`. Это особенность реализации `aiohttp`.

Однако если параметр аннотирован как `bytes` или `StreamReader`, данные извлекаются иначе.

!!! note "Подробнее об объекте `StreamReader` можно узнать **<a href="https://docs.aiohttp.org/en/stable/streams.html" target="_blank">здесь</a>**."

### `bytes`
```python
{!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/02_extract_bytes/01_handler_example.py !}
```
??? info "Внутренний код `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/02_extract_bytes/02_rapidy_code.py !}
    ```

### `StreamReader`
```python
{!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/03_extract_stream_reader/01_handler_example.py !}
```
??? info "Внутренний код `Rapidy`"
    ```python
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/03_extract_stream_reader/02_rapidy_code.py !}
    ```

!!! warning "Валидация `Pydantic` для `StreamReader` не поддерживается."

??? warning "Значение по умолчанию для `StreamReader` задать нельзя."
    Если попытаться установить значение по умолчанию для `Body` с аннотацией `StreamReader` через `default` или `default_factory`,
    будет вызвана ошибка `ParameterCannotUseDefaultError`.

    ```python
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/03_extract_stream_reader/03_stream_reader_cant_default.py !}
    ```
    ```text
    {!> ./docs/docs/server/request/parameters/body/multipart/04_extract_data/03_extract_stream_reader/03_stream_reader_cant_default_text.txt !}
    ```
